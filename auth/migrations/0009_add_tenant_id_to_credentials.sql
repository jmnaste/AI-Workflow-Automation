-- Migration: Add tenant_id to credentials for single-tenant Azure AD support
-- Version: 0.2.0 -> 0.2.1
-- Description: Add optional tenant_id column for MS365 single-tenant OAuth configuration
-- Author: AI Workflow Automation Team
-- Date: 2025-01-13

-- ============================================================
-- Add tenant_id Column to Credentials
-- ============================================================
-- For MS365: stores Azure AD tenant ID (GUID)
-- For Google Workspace: unused (NULL)
-- Allows single-tenant MS365 apps to use tenant-specific OAuth endpoints

ALTER TABLE auth.credentials 
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

-- Add comment for documentation
COMMENT ON COLUMN auth.credentials.tenant_id IS 
'Azure AD Tenant ID for MS365 single-tenant apps. If provided, uses https://login.microsoftonline.com/{tenant_id}/... instead of /common/. NULL for multi-tenant or Google Workspace.';

-- Index for potential future tenant-based queries
CREATE INDEX IF NOT EXISTS idx_credentials_tenant_id ON auth.credentials(tenant_id) WHERE tenant_id IS NOT NULL;

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
VALUES ('auth', 9, '0009_add_tenant_id_to_credentials', 'Add tenant_id column for MS365 single-tenant support')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- Update schema registry (minor version bump: 0.2.0 -> 0.2.1)
UPDATE auth.schema_registry 
SET semver = '0.2.1', ts_key = extract(epoch from now()), applied_at = now()
WHERE service = 'auth';

INSERT INTO auth.schema_registry_history (service, semver, ts_key, applied_at)
VALUES ('auth', '0.2.1', extract(epoch from now()), now());

-- ============================================================
-- Verification Queries (optional - run manually after migration)
-- ============================================================
-- Check column exists:
-- \d auth.credentials

-- Check schema version:
-- SELECT service, semver, applied_at FROM auth.schema_registry WHERE service = 'auth';

-- Example usage:
-- UPDATE auth.credentials 
-- SET tenant_id = '12345678-1234-1234-1234-123456789abc'
-- WHERE provider = 'ms365' AND name = 'your-credential-name';
