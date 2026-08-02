CREATE TABLE properties (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT 'airbnb',
    listing_url TEXT NOT NULL UNIQUE,
    municipality TEXT,
    province TEXT,
    minimum_guests INTEGER,
    maximum_guests INTEGER,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE search_profiles (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    check_in DATE NOT NULL,
    check_out DATE NOT NULL,
    guest_count INTEGER NOT NULL CHECK (guest_count > 0),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (check_out > check_in)
);

CREATE TABLE availability_snapshots (
    id BIGSERIAL PRIMARY KEY,
    property_id BIGINT NOT NULL
        REFERENCES properties(id) ON DELETE CASCADE,

    search_profile_id BIGINT NOT NULL
        REFERENCES search_profiles(id) ON DELETE CASCADE,

    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    status TEXT NOT NULL CHECK (
        status IN (
            'available',
            'not_bookable',
            'unknown',
            'error'
        )
    ),

    currency CHAR(3),
    nightly_price NUMERIC(12, 2),

    result_message TEXT,
    raw_data JSONB,
    screenshot_path TEXT,

    UNIQUE (
        property_id,
        search_profile_id,
        checked_at
    )
);

CREATE TABLE collection_runs (
    id BIGSERIAL PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'running'
        CHECK (status IN ('running', 'completed', 'partial', 'failed')),
    properties_attempted INTEGER NOT NULL DEFAULT 0,
    properties_succeeded INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
);

CREATE INDEX idx_snapshots_property_checked
ON availability_snapshots(property_id, checked_at DESC);

CREATE INDEX idx_snapshots_search_date
ON availability_snapshots(search_profile_id, checked_at DESC);