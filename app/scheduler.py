import logging
import os
import time

import schedule

from app.services.collection_service import run_collection

logger = logging.getLogger(__name__)


def run_scheduled_collection() -> None:
    """Run the competitor collection and log any unhandled failure."""

    logger.info("Scheduled collection started.")

    try:
        run_collection()
        logger.info("Scheduled collection completed successfully.")
    except Exception:
        logger.exception("Scheduled collection failed.")


def start_scheduler(run_time: str = "08:00") -> None:
    """Keep the process open and run collection daily at HH:MM."""

    schedule.every().day.at(run_time).do(run_scheduled_collection)
    logger.info("Scheduler started. Collection will run daily at %s.", run_time)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    start_scheduler(os.getenv("SCHEDULE_TIME", "08:00"))
