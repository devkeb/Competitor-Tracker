-- Run this migration on an existing competitor_tracker database.
-- It is safe to run more than once.

BEGIN;

DROP VIEW IF EXISTS public.competitor_availability_report;

-- Remove the unused minimum_guests column from existing databases.
ALTER TABLE public.properties
    DROP COLUMN IF EXISTS minimum_guests;

ALTER TABLE public.search_profiles
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

ALTER TABLE public.availability_snapshots
    DROP COLUMN IF EXISTS total_price,
    DROP COLUMN IF EXISTS cleaning_fee,
    DROP COLUMN IF EXISTS service_fee,
    DROP COLUMN IF EXISTS rating,
    DROP COLUMN IF EXISTS review_count,
    DROP COLUMN IF EXISTS minimum_nights;

ALTER TABLE public.availability_snapshots
    ALTER COLUMN raw_data SET DEFAULT '{}'::JSONB;

UPDATE public.availability_snapshots
SET raw_data = '{}'::JSONB
WHERE raw_data IS NULL;

ALTER TABLE public.availability_snapshots
    ALTER COLUMN raw_data SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_search_profiles_dates_guests
    ON public.search_profiles(check_in, check_out, guest_count);

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_search_profiles_updated_at
ON public.search_profiles;

CREATE TRIGGER trg_search_profiles_updated_at
BEFORE UPDATE ON public.search_profiles
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

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
