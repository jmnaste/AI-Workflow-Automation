-- Migration: Make created_by nullable in credentials table
-- Version: 0.2.2 -> 0.2.3
-- Description: Fix foreign key constraint issue - created_by should be optional
-- Author: AI Workflow Automation Team
-- Date: 2025-11-14

-- ============================================================
-- Make created_by Nullable
-- ============================================================
-- Issue: Foreign key constraint fails when user ID from JWT doesn't exist
-- Solution: Make created_by nullable to allow credential creation without user reference

ALTER TABLE auth.credentials 
ALTER COLUMN created_by DROP NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN auth.credentials.created_by IS 
'User ID who created this credential. Nullable to handle cases where user may not exist in auth.users (e.g., external admin, SSO users, or deleted users).';

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
VALUES ('auth', 11, '0011_make_credentials_created_by_nullable', 'Make created_by column nullable to fix foreign key constraint issues')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- Update schema registry (patch version bump: 0.2.2 -> 0.2.3)
UPDATE auth.schema_registry 
SET semver = '0.2.3', ts_key = extract(epoch from now()), applied_at = now()
WHERE service = 'auth';

INSERT INTO auth.schema_registry_history (service, semver, ts_key, applied_at)
VALUES ('auth', '0.2.3', extract(epoch from now()), now());

-- ============================================================
-- Verification Queries (optional - run manually after migration)
-- ============================================================
-- Check column is nullable:
-- \d auth.credentials
-- created_by column should NOT show "not null"

-- Check schema version:
-- SELECT service, semver, applied_at FROM auth.schema_registry WHERE service = 'auth';
-- Should show: auth | 0.2.3 | <timestamp>
