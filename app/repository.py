import json
from datetime import date
from typing import Any

from app.database import pool
from app.models import CollectionResult


def get_collection_jobs() -> list[dict[str, Any]]:
    query = """
        SELECT
            p.id AS property_id,
            p.name AS property_name,
            p.listing_url,
            sp.id AS search_profile_id,
            sp.check_in,
            sp.check_out,
            sp.guest_count
        FROM properties p
        CROSS JOIN search_profiles sp
        WHERE p.active = TRUE
          AND sp.active = TRUE
        ORDER BY p.id, sp.id;
    """

    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [column.name for column in cursor.description]

            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]


def save_snapshot(
    property_id: int,
    search_profile_id: int,
    result: CollectionResult,
) -> None:
    query = """
        INSERT INTO availability_snapshots (
            property_id,
            search_profile_id,
            status,
            currency,
            nightly_price,
            total_price,
            cleaning_fee,
            service_fee,
            rating,
            review_count,
            minimum_nights,
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
            %(total_price)s,
            %(cleaning_fee)s,
            %(service_fee)s,
            %(rating)s,
            %(review_count)s,
            %(minimum_nights)s,
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
        "total_price": result.total_price,
        "cleaning_fee": result.cleaning_fee,
        "service_fee": result.service_fee,
        "rating": result.rating,
        "review_count": result.review_count,
        "minimum_nights": result.minimum_nights,
        "result_message": result.result_message,
        "raw_data": json.dumps(result.raw_data),
        "screenshot_path": result.screenshot_path,
    }

    with pool.connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, parameters)

        conn.commit()