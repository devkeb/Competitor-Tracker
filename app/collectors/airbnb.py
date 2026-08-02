from datetime import date
from pathlib import Path
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from playwright.sync_api import BrowserContext, Page, TimeoutError

from app.collectors.base import BaseCollector
from app.models import CollectionResult
from app.services.normalization import extract_currency, normalize_money


class AirbnbCollector(BaseCollector):
    def __init__(
        self,
        context: BrowserContext,
        timeout_ms: int,
        screenshot_directory: str = "screenshots",
    ) -> None:
        self.context = context
        self.timeout_ms = timeout_ms
        self.screenshot_directory = Path(screenshot_directory)
        self.screenshot_directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def build_search_url(
        listing_url: str,
        check_in: date,
        check_out: date,
        guests: int,
    ) -> str:
        """Add dates and guest count to an Airbnb listing URL."""

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
        """Open one listing and return its collected availability result."""

        page = self.context.new_page()
        page.set_default_timeout(self.timeout_ms)

        target_url = self.build_search_url(
            listing_url=listing_url,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
        )

        try:
            page.goto(
                target_url,
                wait_until="domcontentloaded",
            )

            self._dismiss_optional_dialogs(page)
            result = self._extract_result(page)

            # Save evidence when the page loaded but the result was unclear.
            if result.status == "unknown" and not result.screenshot_path:
                result.screenshot_path = self._save_screenshot(
                    page=page,
                    property_id=property_id,
                    reason="unknown",
                )

            return result

        except TimeoutError as exc:
            screenshot = self._save_screenshot(
                page=page,
                property_id=property_id,
                reason="timeout",
            )

            return CollectionResult(
                status="error",
                result_message=f"Page timeout: {exc}",
                screenshot_path=screenshot,
                raw_data={"target_url": target_url},
            )

        except Exception as exc:
            screenshot = self._save_screenshot(
                page=page,
                property_id=property_id,
                reason="unexpected_error",
            )

            return CollectionResult(
                status="error",
                result_message=f"{type(exc).__name__}: {exc}",
                screenshot_path=screenshot,
                raw_data={"target_url": target_url},
            )

        finally:
            page.close()

    def _extract_result(self, page: Page) -> CollectionResult:
        """Extract basic visible availability and price information."""

        # Give client-rendered page elements a brief opportunity to appear.
        page.wait_for_timeout(3000)

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

        unavailable_phrases = [
            "those dates are not available",
            "these dates are not available",
            "not available for your dates",
            "choose different dates",
            "dates are unavailable",
        ]

        lower_text = body_text.lower()

        for phrase in unavailable_phrases:
            if phrase in lower_text:
                return CollectionResult(
                    status="not_bookable",
                    result_message=phrase,
                    raw_data=raw_data,
                )

        price_locator = page.locator(
            "span:has-text('₱'), "
            "span:has-text('PHP')"
        )

        candidate_count = price_locator.count()
        raw_data["price_candidate_count"] = candidate_count

        price_candidates: list[str] = []
        selected_price_text: str | None = None
        nightly_price = None

        # Check every visible currency candidate until a numeric value is parsed.
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

                # Isolate the first currency amount so parent elements that
                # contain several prices or night counts do not confuse parsing.
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

        # Mark the result available only when a valid numeric price exists.
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
                "The page loaded, but no valid numeric price "
                "could be extracted."
            ),
            raw_data=raw_data,
        )

    @staticmethod
    def _dismiss_optional_dialogs(page: Page) -> None:
        """Close optional cookie or modal dialogs when present."""

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
            except (TimeoutError, Exception):
                continue

    def _save_screenshot(
        self,
        page: Page,
        property_id: int,
        reason: str,
    ) -> str:
        """Save a screenshot and return its relative path."""

        path = self.screenshot_directory / (
            f"property_{property_id}_{reason}.png"
        )

        try:
            page.screenshot(
                path=str(path),
                full_page=True,
            )
            return str(path)
        except Exception:
            # Preserve the original collection result if screenshot capture fails.
            return ""
