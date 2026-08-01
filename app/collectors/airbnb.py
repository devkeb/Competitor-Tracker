from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from playwright.sync_api import BrowserContext, Page, TimeoutError
from app.models import CollectionResult
from app.collectors.base import BaseCollector

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

            return self._extract_result(page)

        except TimeoutError as exc:
            screenshot = self._save_screenshot(
                page,
                property_id,
                "timeout",
            )

            return CollectionResult(
                status="error",
                result_message=f"Page timeout: {exc}",
                screenshot_path=screenshot,
            )

        except Exception as exc:
            screenshot = self._save_screenshot(
                page,
                property_id,
                "unexpected_error",
            )

            return CollectionResult(
                status="error",
                result_message=f"{type(exc).__name__}: {exc}",
                screenshot_path=screenshot,
            )

        finally:
            page.close()

    def _extract_result(self, page: Page) -> CollectionResult:
        """
        Implement using selectors verified against the current page.

        Do not classify missing price as automatically unavailable.
        Return 'unknown' when the page does not provide enough evidence.
        """

        page_text = page.locator("body").inner_text()

        return CollectionResult(
            status="unknown",
            result_message="Extractor selectors have not been configured.",
            raw_data={
                "page_title": page.title(),
                "page_url": page.url,
                "body_preview": page_text[:1000],
            },
        )

    @staticmethod
    def _dismiss_optional_dialogs(page: Page) -> None:
        possible_buttons = [
            "button:has-text('Accept')",
            "button:has-text('OK')",
            "button:has-text('Close')",
        ]

        for selector in possible_buttons:
            locator = page.locator(selector).first

            try:
                if locator.is_visible(timeout=1000):
                    locator.click()
                    break
            except TimeoutError:
                continue

    def _save_screenshot(
        self,
        page: Page,
        property_id: int,
        reason: str,
    ) -> str:
        path = self.screenshot_directory / (
            f"property_{property_id}_{reason}.png"
        )

        page.screenshot(path=str(path), full_page=True)
        return str(path)