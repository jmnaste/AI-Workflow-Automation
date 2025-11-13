-- Migration: Drop old tenant tables
-- Version: 0.1.3 -> 0.1.4
-- Description: Remove tenant concept in preparation for credentials model
-- Author: AI Workflow Automation Team
-- Date: 2025-11-12

-- Drop tables (CASCADE removes dependent objects)
DROP TABLE IF EXISTS auth.tenant_tokens CASCADE;
DROP TABLE IF EXISTS auth.tenants CASCADE;

-- Update migration history
INSERT INTO auth.migration_history (schema_name, file_seq, name, notes)
VALUES ('auth', 7, '0007_drop_tenants', 'Drop old tenant tables')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- Update schema registry
UPDATE auth.schema_registry 
SET semver = '0.1.4', ts_key = extract(epoch from now()), applied_at = now()
WHERE service = 'auth';

INSERT INTO auth.schema_registry_history (service, semver, ts_key, applied_at)
VALUES ('auth', '0.1.4', extract(epoch from now()), now());

-- Verification query (optional - run manually)
-- SELECT tablename FROM pg_tables WHERE schemaname = 'auth' AND tablename LIKE '%tenant%';
-- Should return 0 rows
