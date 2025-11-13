-- Migration: Create credentials and credential_tokens tables
-- Version: 0.1.4 -> 0.2.0
-- Description: Implement credentials-based OAuth model (breaking change)
-- Author: AI Workflow Automation Team
-- Date: 2025-11-12

-- ============================================================
-- Credentials Table
-- ============================================================
-- Stores OAuth app configurations + connected account information
CREATE TABLE IF NOT EXISTS auth.credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification (multiple lookup methods)
    name TEXT NOT NULL UNIQUE,           -- Human-readable slug: "acme-ms365"
    display_name TEXT NOT NULL,          -- User-friendly: "Acme Corp MS365"
    provider TEXT NOT NULL,              -- 'ms365' | 'google_workspace'
    
    -- OAuth App Configuration (entered by admin in UI)
    client_id TEXT NOT NULL,
    encrypted_client_secret TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    authorization_url TEXT NOT NULL,
    token_url TEXT NOT NULL,
    scopes TEXT[] NOT NULL,
    
    -- Connected Account Info (populated after OAuth authorization)
    connected_email TEXT,                -- john@acme.com
    external_account_id TEXT,            -- Microsoft's user ID or Google's sub
    connected_display_name TEXT,         -- John Doe
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'connected' | 'error'
    error_message TEXT,
    last_connected_at TIMESTAMPTZ,
    
    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Constraints
    CONSTRAINT credentials_name_check CHECK (name ~ '^[a-z0-9-]+$'),
    CONSTRAINT credentials_status_check CHECK (status IN ('pending', 'connected', 'error')),
    CONSTRAINT credentials_provider_clientid_unique UNIQUE (provider, client_id)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_credentials_provider ON auth.credentials(provider);
CREATE INDEX IF NOT EXISTS idx_credentials_status ON auth.credentials(status);
CREATE INDEX IF NOT EXISTS idx_credentials_email ON auth.credentials(connected_email);
CREATE INDEX IF NOT EXISTS idx_credentials_external_id ON auth.credentials(external_account_id);
CREATE INDEX IF NOT EXISTS idx_credentials_created_by ON auth.credentials(created_by);

-- ============================================================
-- Credential Tokens Table
-- ============================================================
-- Stores encrypted OAuth tokens (access + refresh)
CREATE TABLE IF NOT EXISTS auth.credential_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID NOT NULL REFERENCES auth.credentials(id) ON DELETE CASCADE,
    
    token_type TEXT NOT NULL DEFAULT 'delegated',  -- 'delegated' (future: 'app')
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    scopes TEXT[],
    
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_refreshed_at TIMESTAMPTZ,
    
    -- Only one active token per credential
    CONSTRAINT credential_tokens_credential_unique UNIQUE (credential_id),
    CONSTRAINT credential_tokens_type_check CHECK (token_type IN ('delegated', 'app'))
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_credential_tokens_credential_id ON auth.credential_tokens(credential_id);
CREATE INDEX IF NOT EXISTS idx_credential_tokens_expires_at ON auth.credential_tokens(expires_at);

-- ============================================================
-- Grant Permissions
-- ============================================================
GRANT USAGE ON SCHEMA auth TO app_root;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO app_root;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO app_root;

-- ============================================================
-- Migration History & Schema Registry
-- ============================================================
INSERT INTO auth.migration_history (schema_name, file_seq, name, notes)
VALUES ('auth', 8, '0008_credentials', 'Create credentials and credential_tokens tables')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- Update schema registry (breaking change: 0.1.4 -> 0.2.0)
UPDATE auth.schema_registry 
SET semver = '0.2.0', ts_key = extract(epoch from now()), applied_at = now()
WHERE service = 'auth';

INSERT INTO auth.schema_registry_history (service, semver, ts_key, applied_at)
VALUES ('auth', '0.2.0', extract(epoch from now()), now());

-- ============================================================
-- Verification Queries (optional - run manually after migration)
-- ============================================================
-- Check tables exist:
-- \dt auth.credentials
-- \dt auth.credential_tokens

-- Check indexes:
-- \di auth.idx_credentials_*
-- \di auth.idx_credential_tokens_*

-- Check schema version:
-- SELECT service, semver, applied_at FROM auth.schema_registry WHERE service = 'auth';
