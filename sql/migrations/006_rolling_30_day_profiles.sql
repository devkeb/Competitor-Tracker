-- Optional cleanup for an existing database.
-- The Python application also enforces this rolling window on every run.
-- This keeps exactly 30 one-night check-in dates starting tomorrow.

BEGIN;

UPDATE public.search_profiles
SET
    active = FALSE,
    updated_at = NOW()
WHERE active = TRUE
  AND (
        check_in < (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::DATE + 1
        OR check_in >= (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::DATE + 31
        OR check_out <> check_in + 1
  );

COMMIT;
