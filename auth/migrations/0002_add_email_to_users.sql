-- Add email to auth.users with case-insensitive uniqueness
-- Idempotent and forward-only; safe to re-run

BEGIN;

-- 1) Add nullable email column to users
ALTER TABLE auth.users
    ADD COLUMN IF NOT EXISTS email text NULL;

-- 2) Enforce case-insensitive uniqueness on provided emails
--    (allow multiple NULLs; uniqueness applies only where email IS NOT NULL)
CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique
ON auth.users (lower(email))
WHERE email IS NOT NULL;

-- 3) Versioning and gating footer (manual SQL only)
--    Use SERVICE_SEMVER if provided at session level; otherwise keep current semver.
WITH desired AS (
    SELECT
        COALESCE(
            current_setting('SERVICE_SEMVER', true),
            (SELECT semver FROM auth.schema_registry WHERE service='auth' LIMIT 1),
            '0.1.1'
        ) AS semver,
        to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint AS ts_key
)
INSERT INTO auth.schema_registry(service, semver, ts_key)
SELECT 'auth', semver, ts_key FROM desired
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    applied_at = now();

INSERT INTO auth.schema_registry_history(service, semver, ts_key, applied_at)
SELECT service, semver, ts_key, applied_at
FROM auth.schema_registry
WHERE service = 'auth'
ON CONFLICT DO NOTHING;

-- 4) Record this migration
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', 2, '0002_add_email_to_users.sql', md5('0002_add_email_to_users.sql'), 'add email column with case-insensitive uniqueness')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

COMMIT;
