import logging

from playwright.sync_api import sync_playwright

from app.collectors.airbnb import AirbnbCollector
from app.config import load_settings
from app.repository import (
    ensure_daily_search_profiles_until_year_end,
    get_collection_jobs,
    get_year_end_window,
    manila_today,
    save_snapshot,
)

logger = logging.getLogger(__name__)


def run_collection() -> None:
    """
    Generate one-night profiles through year-end, check every active listing,
    and save one snapshot for every listing/date combination.
    """

    logger.info("Loading application settings...")
    settings = load_settings()

    today = manila_today()
    window = get_year_end_window(today)

    if window is None:
        logger.warning(
            "No one-night date range remains before December 31, %d.",
            today.year,
        )
        return

    start_date, final_check_out = window

    logger.info(
        "Preparing one-night search profiles from %s through %s for %d guest(s)...",
        start_date,
        final_check_out,
        settings.daily_guest_count,
    )

    profile_count = ensure_daily_search_profiles_until_year_end(
        guest_count=settings.daily_guest_count,
        today=today,
    )

    logger.info("Prepared %d daily search profile(s).", profile_count)
    logger.info("Loading collection jobs from PostgreSQL...")

    jobs = get_collection_jobs(
        start_date=start_date,
        final_check_out=final_check_out,
        guest_count=settings.daily_guest_count,
    )

    logger.info("Found %d collection job(s).", len(jobs))

    if not jobs:
        logger.warning(
            "No collection jobs were found. Check that the properties table "
            "contains active listings."
        )
        return

    with sync_playwright() as playwright:
        logger.info("Starting Playwright Chromium...")

        browser = playwright.chromium.launch(headless=settings.headless)
        context = browser.new_context(
            locale="en-PH",
            timezone_id="Asia/Manila",
        )

        collector = AirbnbCollector(
            context=context,
            timeout_ms=settings.page_timeout_ms,
            page_settle_ms=settings.page_settle_ms,
            screenshot_directory="screenshots",
            screenshot_on_error=settings.screenshot_on_error,
            screenshot_on_unknown=settings.screenshot_on_unknown,
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
                        check_in=check_in,
                        check_out=check_out,
                        result=result,
                    )

                    logger.info(
                        "Snapshot saved for property ID %s and check-in %s.",
                        property_id,
                        check_in,
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
