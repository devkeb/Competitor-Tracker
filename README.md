# Competitor Tracker

A Python, Playwright, and PostgreSQL project that checks active Airbnb listing URLs for one-night availability and visible nightly prices.

## Current behavior

Each run:

1. Uses the current date in the `Asia/Manila` timezone.
2. Ignores today and creates **30 one-night search profiles starting tomorrow**.
3. Combines every active property with those 30 generated date profiles.
4. Opens each listing URL with its check-in, check-out, and guest-count parameters.
5. Saves `status`, `currency`, `nightly_price`, stay dates, diagnostic data, and screenshot paths to PostgreSQL.

Example on August 5, 2026:

- Today, August 5, is ignored.
- First stay: August 6 to August 7.
- 30th stay: September 4 to September 5.
- 30 date profiles are generated.
- 14 active listings produce 420 collection jobs.

## Configuration

Copy `.env.example` to `.env` and set the PostgreSQL password.

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@127.0.0.1:5432/competitor_tracker
HEADLESS=false
PAGE_TIMEOUT_MS=45000
PAGE_SETTLE_MS=3000
SCREENSHOT_ON_ERROR=true
SCREENSHOT_ON_UNKNOWN=true
DAILY_GUEST_COUNT=2
EXTRACTION_DAYS=30
SCHEDULE_TIME=08:00
```

`EXTRACTION_DAYS=30` controls how many consecutive check-in dates are processed, starting tomorrow.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Database

For a new database:

```powershell
psql -U postgres -h 127.0.0.1 -d competitor_tracker -f .\schema.sql
```

For an existing database, retain the earlier migrations you already applied. The optional rolling-window cleanup is:

```powershell
psql -U postgres -h 127.0.0.1 -d competitor_tracker -f .\sql\migrations\006_rolling_30_day_profiles.sql
```

The application automatically creates/reactivates the required profiles and deactivates profiles outside the rolling window whenever it runs.

## Run immediately

```powershell
python main.py
```

## Run the Python scheduler

Set `SCHEDULE_TIME` in `.env`, then run:

```powershell
python -m app.scheduler
```

## Verify active profiles

```sql
SELECT
    id,
    check_in,
    check_out,
    guest_count,
    active
FROM public.search_profiles
WHERE active = TRUE
ORDER BY check_in;
```

For the configured guest count, this should show 30 active one-night profiles beginning tomorrow.

## Verify saved snapshots

```sql
SELECT
    id,
    property_id,
    check_in,
    check_out,
    search_profile_id,
    status,
    currency,
    nightly_price,
    result_message,
    checked_at
FROM public.availability_snapshots
ORDER BY checked_at DESC;
```

## Snapshot fields removed

The project no longer uses:

- `total_price`
- `cleaning_fee`
- `service_fee`
- `rating`
- `review_count`
- `minimum_nights`
