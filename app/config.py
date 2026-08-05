import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer.") from exc

    if value < 1:
        raise RuntimeError(f"{name} must be at least 1.")

    return value


@dataclass(frozen=True)
class Settings:
    database_url: str
    headless: bool
    page_timeout_ms: int
    page_settle_ms: int
    screenshot_on_error: bool
    screenshot_on_unknown: bool
    daily_guest_count: int
    extraction_days: int


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured in .env.")

    return Settings(
        database_url=database_url,
        headless=_read_bool("HEADLESS", False),
        page_timeout_ms=_read_positive_int("PAGE_TIMEOUT_MS", 45000),
        page_settle_ms=_read_positive_int("PAGE_SETTLE_MS", 3000),
        screenshot_on_error=_read_bool("SCREENSHOT_ON_ERROR", True),
        screenshot_on_unknown=_read_bool("SCREENSHOT_ON_UNKNOWN", True),
        daily_guest_count=_read_positive_int("DAILY_GUEST_COUNT", 2),
        extraction_days=_read_positive_int("EXTRACTION_DAYS", 30),
    )
