import logging

from playwright.sync_api import sync_playwright

from app.collectors.airbnb import AirbnbCollector
from app.config import load_settings
from app.repository import get_collection_jobs, save_snapshot

logger = logging.getLogger(__name__)
from app.extractors.airbnb_extractor import AirbnbExtractor


def run_collection() -> None:
    """
    Load active properties and search profiles, collect Airbnb data,
    and save one snapshot for every property/search combination.
    """

    logger.info("Loading application settings...")

    settings = load_settings()

    logger.info("Loading collection jobs from PostgreSQL...")

    jobs = get_collection_jobs()

    logger.info("Found %d collection job(s).", len(jobs))

    if not jobs:
        logger.warning(
            "No collection jobs were found. "
            "Check that properties and search_profiles contain active rows."
        )
        return

    with sync_playwright() as playwright:
        logger.info("Starting Playwright Chromium...")

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
            screenshot_directory="screenshots",
        )

        successful_jobs = 0
        failed_jobs = 0

        try:
            for job_number, job in enumerate(jobs, start=1):
                property_id = job["property_id"]
                property_name = job["property_name"]
                listing_url = job["listing_url"]
                search_profile_id = job["search_profile_id"]
                check_in = job["check_in"]
                check_out = job["check_out"]
                guest_count = job["guest_count"]

                logger.info(
                    "Job %d of %d | Checking %s | %s to %s | %d guest(s)",
                    job_number,
                    len(jobs),
                    property_name,
                    check_in,
                    check_out,
                    guest_count,
                )

                try:
                    result = collector.collect(
                        property_id=property_id,
                        listing_url=listing_url,
                        check_in=check_in,
                        check_out=check_out,
                        guests=guest_count,
                    )

                    logger.info(
                        "Collector returned status '%s' for %s.",
                        result.status,
                        property_name,
                    )

                    save_snapshot(
                        property_id=property_id,
                        search_profile_id=search_profile_id,
                        result=result,
                    )

                    logger.info(
                        "Snapshot saved for property ID %s.",
                        property_id,
                    )

                    if result.status == "error":
                        failed_jobs += 1
                    else:
                        successful_jobs += 1

                except Exception:
                    failed_jobs += 1

                    logger.exception(
                        "Job failed for property ID %s: %s",
                        property_id,
                        property_name,
                    )

        finally:
            logger.info("Closing browser context and Chromium...")

            context.close()
            browser.close()

    logger.info(
        "Collection completed. Successful: %d | Failed: %d | Total: %d",
        successful_jobs,
        failed_jobs,
        len(jobs),
    )