-- Store check-in and check-out directly on every availability snapshot.
-- Safe to run more than once.

BEGIN;

DROP VIEW IF EXISTS public.competitor_availability_report;

ALTER TABLE public.availability_snapshots
    ADD COLUMN IF NOT EXISTS check_in DATE,
    ADD COLUMN IF NOT EXISTS check_out DATE;

UPDATE public.availability_snapshots AS snapshot
SET
    check_in = profile.check_in,
    check_out = profile.check_out
FROM public.search_profiles AS profile
WHERE profile.id = snapshot.search_profile_id
  AND (snapshot.check_in IS NULL OR snapshot.check_out IS NULL);

ALTER TABLE public.availability_snapshots
    ALTER COLUMN check_in SET NOT NULL,
    ALTER COLUMN check_out SET NOT NULL;

ALTER TABLE public.availability_snapshots
    DROP CONSTRAINT IF EXISTS chk_availability_dates;

ALTER TABLE public.availability_snapshots
    ADD CONSTRAINT chk_availability_dates
    CHECK (check_out > check_in);

CREATE INDEX IF NOT EXISTS idx_snapshots_stay_dates
    ON public.availability_snapshots(check_in, check_out);

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
    snapshot.search_profile_id,
    profile.name AS search_profile_name,
    snapshot.check_in,
    snapshot.check_out,
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
