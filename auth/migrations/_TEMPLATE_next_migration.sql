-- Template for next Auth manual migration
-- Copy this file, rename to 000X_short_description.sql, and fill placeholders.
-- Wrap DDL in a transaction; keep idempotent with IF NOT EXISTS / ON CONFLICT.

BEGIN;

-- 1) Your DDL changes go here -------------------------------------------------
-- Example:
-- ALTER TABLE auth.users ADD COLUMN example_flag boolean NOT NULL DEFAULT false;


-- 2) Versioning and gating footer (REQUIRED) ----------------------------------
-- Replace <SEMVER>, <REVISION>, <SEQ>, <FILENAME>

-- Alembic version stamp (manual)
CREATE TABLE IF NOT EXISTS auth.alembic_version_auth (
    version_num VARCHAR(32) PRIMARY KEY
);
-- Ensure a row exists, then set to the new revision
INSERT INTO auth.alembic_version_auth(version_num)
VALUES ('<REVISION>')
ON CONFLICT (version_num) DO NOTHING;
UPDATE auth.alembic_version_auth SET version_num = '<REVISION>';

-- Update registry pointer and history
INSERT INTO auth.schema_registry(service, semver, ts_key, alembic_rev)
VALUES (
  'auth',
  '<SEMVER>',
  to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint,
  '<REVISION>'
)
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    alembic_rev = EXCLUDED.alembic_rev,
    applied_at = now();

INSERT INTO auth.schema_registry_history(service, semver, ts_key, alembic_rev, applied_at)
SELECT service, semver, ts_key, alembic_rev, applied_at
FROM auth.schema_registry
WHERE service = 'auth'
ON CONFLICT DO NOTHING;

-- Record this migration in migration_history
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', <SEQ>, '<FILENAME>', md5('<FILENAME>'), 'describe change')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

COMMIT;
