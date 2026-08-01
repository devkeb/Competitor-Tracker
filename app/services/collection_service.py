import logging

from playwright.sync_api import sync_playwright

from app.collectors.airbnb import AirbnbCollector
from app.config import load_settings
from app.repository import get_collection_jobs, save_snapshot

logger = logging.getLogger(__name__)

def run_collection() -> None:
    settings = load_settings()
    jobs = get_collection_jobs()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=settings.headless,
        )

        context = browser.new_context(
            locale="en-PH",
            timezone_id="Asia/Manila",
        )

        collector = AirbnbCollector(
            context=context,
            timeout_ms=settings.page_timeout_ms,
        )

        for job in jobs:
            logger.info(
                "Checking %s for %s to %s",
                job["property_name"],
                job["check_in"],
                job["check_out"],
            )

            result = collector.collect(
                property_id=job["property_id"],
                listing_url=job["listing_url"],
                check_in=job["check_in"],
                check_out=job["check_out"],
                guests=job["guest_count"],
            )

            save_snapshot(
                property_id=job["property_id"],
                search_profile_id=job["search_profile_id"],
                result=result,
            )

        context.close()
        browser.close()