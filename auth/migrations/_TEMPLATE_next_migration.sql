-- Template for next Auth manual migration
-- Copy this file, rename to 000X_short_description.sql, and fill placeholders.
-- Wrap DDL in a transaction; keep idempotent with IF NOT EXISTS / ON CONFLICT.

BEGIN;

-- 1) Your DDL changes go here -------------------------------------------------
-- Examples:
-- (a) Add a nullable column + unique partial index (case-insensitive):
-- ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS email text NULL;
-- CREATE UNIQUE INDEX IF NOT EXISTS users_email_unique ON auth.users (lower(email)) WHERE email IS NOT NULL;
-- (b) Add a NOT NULL column with default for existing rows:
-- ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS example_flag boolean;
-- UPDATE auth.users SET example_flag = false WHERE example_flag IS NULL; -- backfill
-- ALTER TABLE auth.users ALTER COLUMN example_flag SET DEFAULT false;
-- ALTER TABLE auth.users ALTER COLUMN example_flag SET NOT NULL;


-- 2) Registry pointer + history (no Alembic) ----------------------------------
-- Replace <SEMVER>, <SEQ>, <FILENAME>

INSERT INTO auth.schema_registry(service, semver, ts_key)
VALUES (
  'auth',
  COALESCE(current_setting('SERVICE_SEMVER', true), '<SEMVER>'),
  to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint
)
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    applied_at = now();

INSERT INTO auth.schema_registry_history(service, semver, ts_key, applied_at)
SELECT service, semver, ts_key, applied_at
FROM auth.schema_registry
WHERE service = 'auth'
ON CONFLICT DO NOTHING;

-- Record this migration in migration_history
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', <SEQ>, '<FILENAME>', md5('<FILENAME>'), 'describe change')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- Recommended: verify state (optional)
-- SELECT service, semver FROM auth.schema_registry WHERE service='auth';

COMMIT;
