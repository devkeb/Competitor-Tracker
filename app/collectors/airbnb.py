from datetime import date, datetime
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from playwright.sync_api import BrowserContext, Page, TimeoutError

from app.collectors.base import BaseCollector
from app.models import CollectionResult
from app.services.normalization import extract_currency, normalize_money

MANILA_TIMEZONE = ZoneInfo("Asia/Manila")


class AirbnbCollector(BaseCollector):
    def __init__(
        self,
        context: BrowserContext,
        timeout_ms: int,
        page_settle_ms: int = 3000,
        screenshot_directory: str = "screenshots",
        screenshot_on_error: bool = True,
        screenshot_on_unknown: bool = True,
    ) -> None:
        self.context = context
        self.timeout_ms = timeout_ms
        self.page_settle_ms = page_settle_ms
        self.screenshot_directory = Path(screenshot_directory)
        self.screenshot_on_error = screenshot_on_error
        self.screenshot_on_unknown = screenshot_on_unknown
        self.screenshot_directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def build_search_url(
        listing_url: str,
        check_in: date,
        check_out: date,
        guests: int,
    ) -> str:
        """Add check-in, check-out, and guest count to a listing URL."""

        parts = urlsplit(listing_url)
        query = dict(parse_qsl(parts.query))
        query.update(
            {
                "check_in": check_in.isoformat(),
                "check_out": check_out.isoformat(),
                "guests": str(guests),
                "adults": str(guests),
            }
        )

        return urlunsplit(
            (
                parts.scheme,
                parts.netloc,
                parts.path,
                urlencode(query),
                parts.fragment,
            )
        )

    def collect(
        self,
        property_id: int,
        listing_url: str,
        check_in: date,
        check_out: date,
        guests: int,
    ) -> CollectionResult:
        """Open one listing and return its availability result."""

        page = self.context.new_page()
        page.set_default_timeout(self.timeout_ms)

        target_url = self.build_search_url(
            listing_url=listing_url,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
        )

        try:
            page.goto(target_url, wait_until="domcontentloaded")
            self._dismiss_optional_dialogs(page)
            result = self._extract_result(page)

            if (
                result.status == "unknown"
                and self.screenshot_on_unknown
                and not result.screenshot_path
            ):
                result.screenshot_path = self._save_screenshot(
                    page=page,
                    property_id=property_id,
                    check_in=check_in,
                    check_out=check_out,
                    reason="unknown",
                )

            return result

        except TimeoutError as exc:
            screenshot = ""
            if self.screenshot_on_error:
                screenshot = self._save_screenshot(
                    page=page,
                    property_id=property_id,
                    check_in=check_in,
                    check_out=check_out,
                    reason="timeout",
                )

            return CollectionResult(
                status="error",
                result_message=f"Page timeout: {exc}",
                screenshot_path=screenshot or None,
                raw_data={"target_url": target_url},
            )

        except Exception as exc:
            screenshot = ""
            if self.screenshot_on_error:
                screenshot = self._save_screenshot(
                    page=page,
                    property_id=property_id,
                    check_in=check_in,
                    check_out=check_out,
                    reason="unexpected_error",
                )

            return CollectionResult(
                status="error",
                result_message=f"{type(exc).__name__}: {exc}",
                screenshot_path=screenshot or None,
                raw_data={"target_url": target_url},
            )

        finally:
            page.close()

    def _extract_result(self, page: Page) -> CollectionResult:
        """Extract basic visible availability and nightly-price information."""

        page.wait_for_timeout(self.page_settle_ms)

        page_title = page.title()
        page_url = page.url
        body_text = page.locator("body").inner_text()

        raw_data: dict[str, object] = {
            "page_title": page_title,
            "page_url": page_url,
            "body_preview": body_text[:3000],
        }

        if not body_text.strip():
            return CollectionResult(
                status="unknown",
                result_message="The page loaded, but no visible text was found.",
                raw_data=raw_data,
            )

        lower_text = body_text.lower()
        unavailable_phrases = [
            "those dates are not available",
            "these dates are not available",
            "not available for your dates",
            "choose different dates",
            "dates are unavailable",
        ]

        for phrase in unavailable_phrases:
            if phrase in lower_text:
                return CollectionResult(
                    status="not_bookable",
                    result_message=phrase,
                    raw_data=raw_data,
                )

        price_locator = page.locator(
            "span:has-text('₱'), span:has-text('PHP')"
        )
        candidate_count = price_locator.count()
        raw_data["price_candidate_count"] = candidate_count

        price_candidates: list[str] = []
        selected_price_text: str | None = None
        nightly_price = None

        for index in range(candidate_count):
            try:
                locator = price_locator.nth(index)
                if not locator.is_visible():
                    continue

                candidate_text = locator.inner_text().strip()
                if not candidate_text:
                    continue

                if len(price_candidates) < 20:
                    price_candidates.append(candidate_text)

                price_match = re.search(
                    r"(?:₱|PHP\s*)[\s\u00a0]*[0-9][0-9,]*(?:\.[0-9]{1,2})?",
                    candidate_text,
                    flags=re.IGNORECASE,
                )

                if price_match is None:
                    continue

                matched_price_text = price_match.group(0).strip()
                candidate_price = normalize_money(matched_price_text)

                if candidate_price is not None and candidate_price > 0:
                    selected_price_text = matched_price_text
                    nightly_price = candidate_price
                    break

            except Exception:
                continue

        raw_data["price_candidates"] = price_candidates

        if nightly_price is not None and selected_price_text is not None:
            raw_data["price_text"] = selected_price_text
            raw_data["parsed_nightly_price"] = str(nightly_price)

            return CollectionResult(
                status="available",
                currency=extract_currency(selected_price_text) or "PHP",
                nightly_price=nightly_price,
                result_message=(
                    "A visible numeric price was detected and parsed: "
                    f"{selected_price_text}"
                ),
                raw_data=raw_data,
            )

        return CollectionResult(
            status="unknown",
            result_message=(
                "The page loaded, but no valid numeric nightly price "
                "could be extracted."
            ),
            raw_data=raw_data,
        )

    @staticmethod
    def _dismiss_optional_dialogs(page: Page) -> None:
        """Close optional cookie, language, or modal dialogs when present."""

        possible_buttons = [
            "button:has-text('Accept all')",
            "button:has-text('Accept')",
            "button:has-text('OK')",
            "button:has-text('Close')",
            "button[aria-label='Close']",
        ]

        for selector in possible_buttons:
            locator = page.locator(selector).first

            try:
                if locator.is_visible(timeout=1000):
                    locator.click()
                    break
            except Exception:
                continue

    def _save_screenshot(
        self,
        page: Page,
        property_id: int,
        check_in: date,
        check_out: date,
        reason: str,
    ) -> str:
        """Save a uniquely named screenshot and return its relative path."""

        now = datetime.now(MANILA_TIMEZONE)
        run_directory = self.screenshot_directory / now.strftime("%Y-%m-%d")
        run_directory.mkdir(parents=True, exist_ok=True)

        filename = (
            f"property_{property_id}_{check_in.isoformat()}_"
            f"{check_out.isoformat()}_{reason}_{now:%H%M%S%f}.png"
        )
        path = run_directory / filename

        try:
            page.screenshot(path=str(path), full_page=True)
            return str(path)
        except Exception:
            return ""
