-- Template for next API manual migration
-- Copy this file, rename to 000X_short_description.sql, and fill placeholders.
-- Wrap DDL in a transaction; keep idempotent with IF NOT EXISTS / ON CONFLICT.

BEGIN;

-- 1) Your DDL changes go here -------------------------------------------------
-- Examples:
-- (a) Add a nullable column:
-- ALTER TABLE api.settings ADD COLUMN IF NOT EXISTS extra jsonb;
-- (b) Add a NOT NULL column with backfill:
-- ALTER TABLE api.settings ADD COLUMN IF NOT EXISTS enabled boolean;
-- UPDATE api.settings SET enabled = true WHERE enabled IS NULL; -- backfill existing rows
-- ALTER TABLE api.settings ALTER COLUMN enabled SET DEFAULT true;
-- ALTER TABLE api.settings ALTER COLUMN enabled SET NOT NULL;
-- (c) Create a new table:
-- CREATE TABLE IF NOT EXISTS api.example (
--     id bigserial PRIMARY KEY,
--     name text NOT NULL,
--     created_at timestamptz NOT NULL DEFAULT now()
-- );
-- (d) Indexes:
-- CREATE INDEX IF NOT EXISTS example_name_idx ON api.example (lower(name));

-- 2) Record this migration in migration_history -------------------------------
-- Replace <SEQ>, <FILENAME>
INSERT INTO api.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('api', <SEQ>, '<FILENAME>', md5('<FILENAME>'), 'describe change')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- Recommended: verification (optional) ---------------------------------------
-- SELECT schema_name, file_seq, name, applied_at FROM api.migration_history ORDER BY file_seq DESC LIMIT 5;
-- \dt api.*

COMMIT;
