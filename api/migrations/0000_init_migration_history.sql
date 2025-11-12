-- Initialize manual SQL migrations history for the api schema
-- Idempotent: safe to run multiple times

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

-- 3) Create migration history table
CREATE TABLE IF NOT EXISTS api.migration_history (
    id           bigserial PRIMARY KEY,
    schema_name  text        NOT NULL,
    file_seq     int         NOT NULL,
    name         text        NOT NULL, -- full filename e.g. 0001_api_bootstrap.sql
    checksum     text        NULL,     -- optional md5 of file contents
    applied_by   text        NOT NULL DEFAULT current_user,
    applied_at   timestamptz NOT NULL DEFAULT now(),
    notes        text        NULL,
    CONSTRAINT uq_api_migration_history_schema_seq UNIQUE (schema_name, file_seq),
    CONSTRAINT uq_api_migration_history_schema_name UNIQUE (schema_name, name)
);

COMMIT;
