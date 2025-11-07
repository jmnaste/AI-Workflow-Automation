-- Health-check migration for debugging psql-based runs
-- Idempotent and non-intrusive: DOES NOT change schema_registry pointer.
-- Safe to re-run. Intended purely to validate the psql execution path and DB connectivity.

BEGIN;

-- 1) Create a simple health log table (idempotent)
CREATE TABLE IF NOT EXISTS auth.migration_health_log (
    id bigserial PRIMARY KEY,
    note text NOT NULL,
    db text NULL,
    usr text NULL,
    search_path text NULL,
    server_version text NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);

-- 2) Insert one diagnostic row so we can confirm execution via psql
INSERT INTO auth.migration_health_log (note, db, usr, search_path, server_version)
VALUES (
    'psql test 9999',
    current_database(),
    current_user,
    current_setting('search_path', true),
    version()
);

-- 3) DO NOT modify schema_registry in this file
--    This script is strictly for path/connection verification.

-- 4) Do not record this script in auth.migration_history; it's a pure health check.

-- 5) Output list of applied migrations for debugging (no changes made)
SELECT schema_name, file_seq, name, applied_by, applied_at, notes
FROM auth.migration_history
WHERE schema_name = 'auth'
ORDER BY file_seq;

COMMIT;
