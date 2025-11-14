-- Migration: Remove provider+client_id unique constraint from credentials
-- Version: 0.2.1 -> 0.2.2
-- Description: Allow multiple credentials with same provider and client_id for different configurations
-- Author: AI Workflow Automation Team
-- Date: 2025-01-13

-- ============================================================
-- Drop Unnecessary Unique Constraint
-- ============================================================
-- The provider+client_id unique constraint is too restrictive.
-- Valid use cases for multiple credentials with same OAuth app:
-- - Testing different configurations (redirect URIs, scopes, tenant IDs)
-- - Separate credentials for different environments
-- - Maintaining old credentials while testing new ones
--
-- The credential 'name' remains unique, which is sufficient.

ALTER TABLE auth.credentials 
DROP CONSTRAINT IF EXISTS credentials_provider_clientid_unique;

-- ============================================================
-- Grant Permissions (idempotent)
-- ============================================================
GRANT USAGE ON SCHEMA auth TO app_root;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO app_root;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO app_root;

-- ============================================================
-- Migration History & Schema Registry
-- ============================================================
INSERT INTO auth.migration_history (schema_name, file_seq, name, notes)
VALUES ('auth', 10, '0010_remove_provider_clientid_unique_constraint', 'Remove overly restrictive provider+client_id unique constraint')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- Update schema registry (patch version bump: 0.2.1 -> 0.2.2)
UPDATE auth.schema_registry 
SET semver = '0.2.2', ts_key = extract(epoch from now()), applied_at = now()
WHERE service = 'auth';

INSERT INTO auth.schema_registry_history (service, semver, ts_key, applied_at)
VALUES ('auth', '0.2.2', extract(epoch from now()), now());

-- ============================================================
-- Verification Queries (optional - run manually after migration)
-- ============================================================
-- Check constraint removed:
-- \d auth.credentials
-- Should only show credentials_name_key, not credentials_provider_clientid_unique

-- Check schema version:
-- SELECT service, semver, applied_at FROM auth.schema_registry WHERE service = 'auth';
