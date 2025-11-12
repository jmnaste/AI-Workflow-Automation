-- Manual bootstrap for API schema: create minimal settings table
-- Idempotent: uses IF NOT EXISTS and ON CONFLICT where applicable

BEGIN;

-- 1) Ensure schema exists
CREATE SCHEMA IF NOT EXISTS api;

-- 2) Grant privileges to application user
GRANT USAGE ON SCHEMA api TO app_root;
GRANT CREATE ON SCHEMA api TO app_root;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA api TO app_root;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA api TO app_root;

-- Set default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA api GRANT ALL PRIVILEGES ON TABLES TO app_root;
ALTER DEFAULT PRIVILEGES IN SCHEMA api GRANT ALL PRIVILEGES ON SEQUENCES TO app_root;

-- 3) Settings table: simple key/value store for API-level configuration
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
