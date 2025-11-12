-- Add tenant_tokens table for OAuth credential storage
-- Stores encrypted access and refresh tokens per tenant
-- Idempotent: uses IF NOT EXISTS

BEGIN;

-- Create tenant_tokens table
CREATE TABLE IF NOT EXISTS auth.tenant_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    token_type text NOT NULL CHECK (token_type IN ('app', 'delegated')),
    encrypted_access_token text NOT NULL,
    encrypted_refresh_token text,  -- Nullable for app-only flows
    scopes text[] NOT NULL DEFAULT '{}',
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_refreshed_at timestamptz,
    UNIQUE(tenant_id)  -- One token set per tenant
);

-- Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_tenant_tokens_tenant_id ON auth.tenant_tokens(tenant_id);
CREATE INDEX IF NOT EXISTS idx_tenant_tokens_expires_at ON auth.tenant_tokens(expires_at);

-- Grant privileges to app_root user
GRANT ALL PRIVILEGES ON auth.tenant_tokens TO app_root;

-- Update schema registry to version 0.1.3
WITH desired AS (
    SELECT
        COALESCE(
            current_setting('SERVICE_SEMVER', true),
            '0.1.3'
        ) AS semver,
        to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint AS ts_key
)
INSERT INTO auth.schema_registry(service, semver, ts_key)
SELECT 'auth', semver, ts_key FROM desired
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    applied_at = now();

-- Record in schema registry history
INSERT INTO auth.schema_registry_history(service, semver, ts_key, applied_at)
SELECT service, semver, ts_key, applied_at
FROM auth.schema_registry
WHERE service = 'auth'
ON CONFLICT DO NOTHING;

-- Record this migration
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', 6, '0006_tenant_tokens.sql', md5('0006_tenant_tokens.sql'), 'add tenant_tokens table for OAuth credentials')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

COMMIT;
