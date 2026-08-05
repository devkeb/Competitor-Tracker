from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.database import pool
from app.models import CollectionResult

MANILA_TIMEZONE = ZoneInfo("Asia/Manila")


def manila_today() -> date:
    """Return the current calendar date in the Philippines."""

    return datetime.now(MANILA_TIMEZONE).date()


def get_collection_window(
    today: date | None = None,
    extraction_days: int = 30,
) -> tuple[date, date]:
    """
    Return the rolling one-night collection window.

    The first check-in is tomorrow. ``extraction_days`` is the number of
    consecutive check-in dates to generate. The returned second date is the
    final check-out boundary (exclusive for check-in generation).

    Example for 30 days:
        first check-in = tomorrow
        final check-in = tomorrow + 29 days
        final check-out = tomorrow + 30 days
    """

    if extraction_days < 1:
        raise ValueError("extraction_days must be at least 1.")

    reference_date = today or manila_today()
    start_date = reference_date + timedelta(days=1)
    final_check_out = start_date + timedelta(days=extraction_days)

    return start_date, final_check_out


def ensure_daily_search_profiles(
    guest_count: int = 2,
    extraction_days: int = 30,
    today: date | None = None,
) -> int:
    """Create or reactivate one-night profiles for the rolling date window."""

    if guest_count < 1:
        raise ValueError("guest_count must be at least 1.")

    start_date, final_check_out = get_collection_window(
        today=today,
        extraction_days=extraction_days,
    )

    profiles: list[dict[str, Any]] = []
    check_in = start_date

    while check_in < final_check_out:
        check_out = check_in + timedelta(days=1)

        profiles.append(
            {
                "name": (
                    f"Daily availability - {check_in.isoformat()} - "
                    f"{guest_count} guest(s)"
                ),
                "check_in": check_in,
                "check_out": check_out,
                "guest_count": guest_count,
            }
        )
        check_in = check_out

    insert_query = """
        INSERT INTO public.search_profiles (
            name,
            check_in,
            check_out,
            guest_count,
            active
        )
        VALUES (
            %(name)s,
            %(check_in)s,
            %(check_out)s,
            %(guest_count)s,
            TRUE
        )
        ON CONFLICT (check_in, check_out, guest_count)
        DO UPDATE SET
            name = EXCLUDED.name,
            active = TRUE,
            updated_at = NOW();
    """

    deactivate_query = """
        UPDATE public.search_profiles
        SET
            active = FALSE,
            updated_at = NOW()
        WHERE guest_count = %(guest_count)s
          AND active = TRUE
          AND (
                check_in < %(start_date)s
                OR check_in >= %(final_check_out)s
                OR check_out > %(final_check_out)s
                OR check_out <> check_in + 1
          );
    """

    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                deactivate_query,
                {
                    "guest_count": guest_count,
                    "start_date": start_date,
                    "final_check_out": final_check_out,
                },
            )
            cursor.executemany(insert_query, profiles)
        conn.commit()

    return len(profiles)


def get_collection_jobs(
    start_date: date,
    final_check_out: date,
    guest_count: int,
) -> list[dict[str, Any]]:
    """Load every active listing and rolling daily-profile combination."""

    query = """
        SELECT
            property.id AS property_id,
            property.name AS property_name,
            property.listing_url,
            profile.id AS search_profile_id,
            profile.name AS search_profile_name,
            profile.check_in,
            profile.check_out,
            profile.guest_count
        FROM public.properties AS property
        CROSS JOIN public.search_profiles AS profile
        WHERE property.active = TRUE
          AND profile.active = TRUE
          AND profile.guest_count = %(guest_count)s
          AND profile.check_in >= %(start_date)s
          AND profile.check_in < %(final_check_out)s
          AND profile.check_out <= %(final_check_out)s
          AND profile.check_out = profile.check_in + 1
        ORDER BY
            property.id,
            profile.check_in;
    """

    parameters = {
        "guest_count": guest_count,
        "start_date": start_date,
        "final_check_out": final_check_out,
    }

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query, parameters)
            jobs = cursor.fetchall()

    return jobs


def save_snapshot(
    property_id: int,
    search_profile_id: int,
    check_in: date,
    check_out: date,
    result: CollectionResult,
) -> None:
    """Save one collected result into availability_snapshots."""

    query = """
        INSERT INTO public.availability_snapshots (
            property_id,
            check_in,
            check_out,
            search_profile_id,
            status,
            currency,
            nightly_price,
            result_message,
            raw_data,
            screenshot_path
        )
        VALUES (
            %(property_id)s,
            %(check_in)s,
            %(check_out)s,
            %(search_profile_id)s,
            %(status)s,
            %(currency)s,
            %(nightly_price)s,
            %(result_message)s,
            %(raw_data)s,
            %(screenshot_path)s
        );
    """

    parameters = {
        "property_id": property_id,
        "search_profile_id": search_profile_id,
        "check_in": check_in,
        "check_out": check_out,
        "status": result.status,
        "currency": result.currency,
        "nightly_price": result.nightly_price,
        "result_message": result.result_message,
        "raw_data": Jsonb(result.raw_data),
        "screenshot_path": result.screenshot_path,
    }

    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, parameters)
        conn.commit()
