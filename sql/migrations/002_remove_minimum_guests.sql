-- Remove minimum_guests from an existing competitor_tracker database.
-- Safe to run more than once.

BEGIN;

DROP VIEW IF EXISTS public.competitor_availability_report;

ALTER TABLE public.properties
    DROP COLUMN IF EXISTS minimum_guests;

CREATE OR REPLACE VIEW public.competitor_availability_report AS
SELECT
    snapshot.id AS snapshot_id,
    property.id AS property_id,
    property.name AS property_name,
    property.platform,
    property.listing_url,
    property.municipality,
    property.province,
    property.maximum_guests,
    profile.id AS search_profile_id,
    profile.name AS search_profile_name,
    profile.check_in,
    profile.check_out,
    profile.guest_count,
    snapshot.status,
    snapshot.currency,
    snapshot.nightly_price,
    snapshot.result_message,
    snapshot.checked_at,
    snapshot.screenshot_path
FROM public.availability_snapshots AS snapshot
JOIN public.properties AS property
    ON property.id = snapshot.property_id
JOIN public.search_profiles AS profile
    ON profile.id = snapshot.search_profile_id;

COMMIT;
