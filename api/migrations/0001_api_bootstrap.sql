-- Manual bootstrap for API schema: create minimal settings table
-- Idempotent: uses IF NOT EXISTS and ON CONFLICT where applicable

BEGIN;

-- Ensure schema exists
CREATE SCHEMA IF NOT EXISTS api;

-- Settings table: simple key/value store for API-level configuration
CREATE TABLE IF NOT EXISTS api.settings (
    id uuid PRIMARY KEY,
    key text NOT NULL UNIQUE,
    value text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Record this migration (without altering any global version tables)
INSERT INTO api.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('api', 1, '0001_api_bootstrap.sql', md5('0001_api_bootstrap.sql'), 'create api.settings table')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

COMMIT;
