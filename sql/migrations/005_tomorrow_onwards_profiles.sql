-- Optional cleanup for existing databases.
-- The application also enforces this rule automatically on every run.

BEGIN;

UPDATE public.search_profiles
SET
    active = FALSE,
    updated_at = NOW()
WHERE active = TRUE
  AND check_in <= (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::DATE;

COMMIT;
