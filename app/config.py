import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    headless: bool
    page_timeout_ms: int
    screenshot_on_error: bool


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    return Settings(
        database_url=database_url,
        headless=os.getenv("HEADLESS", "false").lower() == "true",
        page_timeout_ms=int(os.getenv("PAGE_TIMEOUT_MS", "45000")),
        screenshot_on_error=(
            os.getenv("SCREENSHOT_ON_ERROR", "true").lower() == "true"
        ),
    )