-- Competitor Tracker schema for PostgreSQL

CREATE TABLE IF NOT EXISTS public.properties (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'airbnb',
    listing_url TEXT NOT NULL UNIQUE,
    municipality TEXT,
    province TEXT,
    maximum_guests INTEGER,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_properties_maximum_guests
        CHECK (maximum_guests IS NULL OR maximum_guests > 0)
);

CREATE TABLE IF NOT EXISTS public.search_profiles (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    guest_count INTEGER NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_search_profiles_dates
        CHECK (check_out > check_in),
    CONSTRAINT chk_search_profiles_guest_count
        CHECK (guest_count > 0),
    CONSTRAINT uq_search_profiles_dates_guests
        UNIQUE (check_in, check_out, guest_count)
);

CREATE TABLE IF NOT EXISTS public.collection_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running',
    properties_attempted INTEGER NOT NULL DEFAULT 0,
    properties_succeeded INTEGER NOT NULL DEFAULT 0,
    properties_failed INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,

    CONSTRAINT chk_collection_runs_status
        CHECK (status IN ('running', 'completed', 'partial', 'failed')),
    CONSTRAINT chk_collection_runs_attempted
        CHECK (properties_attempted >= 0),
    CONSTRAINT chk_collection_runs_succeeded
        CHECK (properties_succeeded >= 0),
    CONSTRAINT chk_collection_runs_failed
        CHECK (properties_failed >= 0)
);

CREATE TABLE IF NOT EXISTS public.availability_snapshots (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT NOT NULL
        REFERENCES public.properties(id)
        ON DELETE CASCADE,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    search_profile_id BIGINT NOT NULL
        REFERENCES public.search_profiles(id)
        ON DELETE CASCADE,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL,
    currency CHAR(3),
    nightly_price NUMERIC(12, 2),
    result_message TEXT,
    raw_data JSONB NOT NULL DEFAULT '{}'::JSONB,
    screenshot_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_availability_dates
        CHECK (check_out > check_in),
    CONSTRAINT chk_availability_status
        CHECK (status IN ('available', 'not_bookable', 'unknown', 'error')),
    CONSTRAINT chk_nightly_price
        CHECK (nightly_price IS NULL OR nightly_price >= 0)
);

CREATE INDEX IF NOT EXISTS idx_properties_active
    ON public.properties(active);

CREATE INDEX IF NOT EXISTS idx_search_profiles_active_dates
    ON public.search_profiles(active, guest_count, check_in, check_out);

CREATE INDEX IF NOT EXISTS idx_snapshots_property_checked
    ON public.availability_snapshots(property_id, checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_snapshots_search_date
    ON public.availability_snapshots(search_profile_id, checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_snapshots_stay_dates
    ON public.availability_snapshots(check_in, check_out);

CREATE INDEX IF NOT EXISTS idx_snapshots_status
    ON public.availability_snapshots(status);

CREATE INDEX IF NOT EXISTS idx_snapshots_raw_data
    ON public.availability_snapshots USING GIN(raw_data);

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_properties_updated_at
ON public.properties;

CREATE TRIGGER trg_properties_updated_at
BEFORE UPDATE ON public.properties
FOR EACH ROW
EXECUTE FUNCTION public.set_updated_at();

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
    snapshot.check_in,
    snapshot.check_out,
    property.name AS property_name,
    property.platform,
    property.listing_url,
    property.municipality,
    property.province,
    property.maximum_guests,
    profile.id AS search_profile_id,
    profile.name AS search_profile_name,
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
