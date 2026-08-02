from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.database import pool
from app.models import CollectionResult


def get_collection_jobs() -> list[dict[str, Any]]:
    """
    Load every active property and active search-profile combination.

    Each returned row becomes one collection job.
    """

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

        ORDER BY
            property.id,
            profile.id;
    """

    with pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cursor:
            cursor.execute(query)
            jobs = cursor.fetchall()

    return jobs


def save_snapshot(
    property_id: int,
    search_profile_id: int,
    result: CollectionResult,
) -> None:
    """Save one collected result into availability_snapshots."""

    query = """
        INSERT INTO public.availability_snapshots (
            property_id,
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