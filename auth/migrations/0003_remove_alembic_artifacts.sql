-- Remove Alembic artifacts now that we rely solely on manual SQL
-- Forward-only, idempotent where possible

BEGIN;

-- 1) Drop the Alembic version table if present
DROP TABLE IF EXISTS auth.alembic_version_auth;

-- 2) Remove alembic_rev from registry tables if present
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='auth' AND table_name='schema_registry' AND column_name='alembic_rev'
    ) THEN
        EXECUTE 'ALTER TABLE auth.schema_registry DROP COLUMN alembic_rev';
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='auth' AND table_name='schema_registry_history' AND column_name='alembic_rev'
    ) THEN
        EXECUTE 'ALTER TABLE auth.schema_registry_history DROP COLUMN alembic_rev';
    END IF;
END$$;

-- 3) Record this migration
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', 3, '0003_remove_alembic_artifacts.sql', md5('0003_remove_alembic_artifacts.sql'), 'drop Alembic version table and alembic_rev columns')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

COMMIT;
