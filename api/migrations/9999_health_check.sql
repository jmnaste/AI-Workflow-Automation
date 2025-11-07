-- API health-check migration for debugging psql-based runs
-- Idempotent and non-intrusive: does NOT change any versions or pointers.
-- Safe to re-run. Intended purely to validate the psql execution path and DB connectivity.

BEGIN;

-- 1) Ensure schema exists (no-op if already present)
CREATE SCHEMA IF NOT EXISTS api;

-- 2) Create a simple health log table (idempotent)
CREATE TABLE IF NOT EXISTS api.migration_health_log (
    id bigserial PRIMARY KEY,
    note text NOT NULL,
    db text NULL,
    usr text NULL,
    search_path text NULL,
    server_version text NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);

-- 3) Insert one diagnostic row so we can confirm execution via psql
INSERT INTO api.migration_health_log (note, db, usr, search_path, server_version)
VALUES (
    'psql test api 9999',
    current_database(),
    current_user,
    current_setting('search_path', true),
    version()
);

-- 4) Do not record this script in api.migration_history; it's a pure health check.

-- 5) Output list of applied api migrations for debugging (no changes made)
SELECT schema_name, file_seq, name, applied_by, applied_at, notes
FROM api.migration_history
WHERE schema_name = 'api'
ORDER BY file_seq;

COMMIT;