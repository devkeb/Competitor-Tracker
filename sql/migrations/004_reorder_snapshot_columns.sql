-- Rebuild availability_snapshots so the physical column order is:
-- id, property_id, check_in, check_out, search_profile_id, ...
-- PostgreSQL cannot directly move existing columns, so this migration
-- copies the data into a replacement table.
--
-- Compatibility:
-- * Preserves collection_run_id when the old table has it.
-- * Preserves created_at when the old table has it.
-- * Uses checked_at as created_at when the old table has no created_at.

BEGIN;

DROP VIEW IF EXISTS public.competitor_availability_report;
DROP TABLE IF EXISTS public.availability_snapshots_new;

-- Ensure the stay-date columns exist even if migration 003 was not run.
ALTER TABLE public.availability_snapshots
    ADD COLUMN IF NOT EXISTS check_in DATE,
    ADD COLUMN IF NOT EXISTS check_out DATE;

-- Backfill stay dates from the linked search profile.
UPDATE public.availability_snapshots AS snapshot
SET
    check_in = profile.check_in,
    check_out = profile.check_out
FROM public.search_profiles AS profile
WHERE profile.id = snapshot.search_profile_id
  AND (snapshot.check_in IS NULL OR snapshot.check_out IS NULL);

-- Stop if any row still has no dates. This avoids silently losing data.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.availability_snapshots
        WHERE check_in IS NULL OR check_out IS NULL
    ) THEN
        RAISE EXCEPTION
            'Some availability_snapshots rows have no check_in/check_out and could not be matched to search_profiles.';
    END IF;
END;
$$;

-- Keep the existing sequence alive while the old table is replaced.
ALTER SEQUENCE public.availability_snapshots_id_seq OWNED BY NONE;

DO $$
DECLARE
    has_collection_run_id BOOLEAN;
    has_created_at BOOLEAN;
    created_at_expression TEXT;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'availability_snapshots'
          AND column_name = 'collection_run_id'
    )
    INTO has_collection_run_id;

    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'availability_snapshots'
          AND column_name = 'created_at'
    )
    INTO has_created_at;

    created_at_expression := CASE
        WHEN has_created_at THEN 'created_at'
        ELSE 'COALESCE(checked_at, NOW())'
    END;

    IF has_collection_run_id THEN
        EXECUTE $create_table$
            CREATE TABLE public.availability_snapshots_new (
                id BIGINT NOT NULL DEFAULT nextval(
                    'public.availability_snapshots_id_seq'::regclass
                ),
                property_id BIGINT NOT NULL,
                check_in DATE NOT NULL,
                check_out DATE NOT NULL,
                search_profile_id BIGINT NOT NULL,
                collection_run_id BIGINT,
                checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                status TEXT NOT NULL,
                currency CHAR(3),
                nightly_price NUMERIC(12, 2),
                result_message TEXT,
                raw_data JSONB NOT NULL DEFAULT '{}'::JSONB,
                screenshot_path TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                CONSTRAINT availability_snapshots_new_pkey
                    PRIMARY KEY (id),
                CONSTRAINT availability_snapshots_new_property_fkey
                    FOREIGN KEY (property_id)
                    REFERENCES public.properties(id)
                    ON DELETE CASCADE,
                CONSTRAINT availability_snapshots_new_profile_fkey
                    FOREIGN KEY (search_profile_id)
                    REFERENCES public.search_profiles(id)
                    ON DELETE CASCADE,
                CONSTRAINT availability_snapshots_new_run_fkey
                    FOREIGN KEY (collection_run_id)
                    REFERENCES public.collection_runs(id)
                    ON DELETE SET NULL,
                CONSTRAINT chk_availability_dates_new
                    CHECK (check_out > check_in),
                CONSTRAINT chk_availability_status_new
                    CHECK (
                        status IN (
                            'available',
                            'not_bookable',
                            'unknown',
                            'error'
                        )
                    ),
                CONSTRAINT chk_nightly_price_new
                    CHECK (nightly_price IS NULL OR nightly_price >= 0)
            )
        $create_table$;

        EXECUTE format(
            $copy_data$
                INSERT INTO public.availability_snapshots_new (
                    id,
                    property_id,
                    check_in,
                    check_out,
                    search_profile_id,
                    collection_run_id,
                    checked_at,
                    status,
                    currency,
                    nightly_price,
                    result_message,
                    raw_data,
                    screenshot_path,
                    created_at
                )
                SELECT
                    id,
                    property_id,
                    check_in,
                    check_out,
                    search_profile_id,
                    collection_run_id,
                    checked_at,
                    status,
                    currency,
                    nightly_price,
                    result_message,
                    raw_data,
                    screenshot_path,
                    %s
                FROM public.availability_snapshots
            $copy_data$,
            created_at_expression
        );
    ELSE
        EXECUTE $create_table$
            CREATE TABLE public.availability_snapshots_new (
                id BIGINT NOT NULL DEFAULT nextval(
                    'public.availability_snapshots_id_seq'::regclass
                ),
                property_id BIGINT NOT NULL,
                check_in DATE NOT NULL,
                check_out DATE NOT NULL,
                search_profile_id BIGINT NOT NULL,
                checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                status TEXT NOT NULL,
                currency CHAR(3),
                nightly_price NUMERIC(12, 2),
                result_message TEXT,
                raw_data JSONB NOT NULL DEFAULT '{}'::JSONB,
                screenshot_path TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                CONSTRAINT availability_snapshots_new_pkey
                    PRIMARY KEY (id),
                CONSTRAINT availability_snapshots_new_property_fkey
                    FOREIGN KEY (property_id)
                    REFERENCES public.properties(id)
                    ON DELETE CASCADE,
                CONSTRAINT availability_snapshots_new_profile_fkey
                    FOREIGN KEY (search_profile_id)
                    REFERENCES public.search_profiles(id)
                    ON DELETE CASCADE,
                CONSTRAINT chk_availability_dates_new
                    CHECK (check_out > check_in),
                CONSTRAINT chk_availability_status_new
                    CHECK (
                        status IN (
                            'available',
                            'not_bookable',
                            'unknown',
                            'error'
                        )
                    ),
                CONSTRAINT chk_nightly_price_new
                    CHECK (nightly_price IS NULL OR nightly_price >= 0)
            )
        $create_table$;

        EXECUTE format(
            $copy_data$
                INSERT INTO public.availability_snapshots_new (
                    id,
                    property_id,
                    check_in,
                    check_out,
                    search_profile_id,
                    checked_at,
                    status,
                    currency,
                    nightly_price,
                    result_message,
                    raw_data,
                    screenshot_path,
                    created_at
                )
                SELECT
                    id,
                    property_id,
                    check_in,
                    check_out,
                    search_profile_id,
                    checked_at,
                    status,
                    currency,
                    nightly_price,
                    result_message,
                    raw_data,
                    screenshot_path,
                    %s
                FROM public.availability_snapshots
            $copy_data$,
            created_at_expression
        );
    END IF;
END;
$$;

DROP TABLE public.availability_snapshots;
ALTER TABLE public.availability_snapshots_new
    RENAME TO availability_snapshots;

ALTER TABLE public.availability_snapshots
    RENAME CONSTRAINT availability_snapshots_new_pkey
        TO availability_snapshots_pkey;
ALTER TABLE public.availability_snapshots
    RENAME CONSTRAINT availability_snapshots_new_property_fkey
        TO availability_snapshots_property_id_fkey;
ALTER TABLE public.availability_snapshots
    RENAME CONSTRAINT availability_snapshots_new_profile_fkey
        TO availability_snapshots_search_profile_id_fkey;
ALTER TABLE public.availability_snapshots
    RENAME CONSTRAINT chk_availability_dates_new
        TO chk_availability_dates;
ALTER TABLE public.availability_snapshots
    RENAME CONSTRAINT chk_availability_status_new
        TO chk_availability_status;
ALTER TABLE public.availability_snapshots
    RENAME CONSTRAINT chk_nightly_price_new
        TO chk_nightly_price;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.table_constraints
        WHERE constraint_schema = 'public'
          AND table_name = 'availability_snapshots'
          AND constraint_name = 'availability_snapshots_new_run_fkey'
    ) THEN
        ALTER TABLE public.availability_snapshots
            RENAME CONSTRAINT availability_snapshots_new_run_fkey
                TO availability_snapshots_collection_run_id_fkey;
    END IF;
END;
$$;

ALTER SEQUENCE public.availability_snapshots_id_seq
    OWNED BY public.availability_snapshots.id;

SELECT setval(
    'public.availability_snapshots_id_seq',
    COALESCE(
        (SELECT MAX(id) FROM public.availability_snapshots),
        0
    ) + 1,
    FALSE
);

CREATE INDEX idx_snapshots_property_checked
    ON public.availability_snapshots(property_id, checked_at DESC);

CREATE INDEX idx_snapshots_search_date
    ON public.availability_snapshots(search_profile_id, checked_at DESC);

CREATE INDEX idx_snapshots_stay_dates
    ON public.availability_snapshots(check_in, check_out);

CREATE INDEX idx_snapshots_status
    ON public.availability_snapshots(status);

CREATE INDEX idx_snapshots_raw_data
    ON public.availability_snapshots USING GIN(raw_data);

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
    snapshot.search_profile_id,
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

COMMIT;