-- Migration: Webhook Subscriptions Tracking
-- Purpose: Track active MS365 and Google Workspace webhook subscriptions
-- Schema: api
-- Version: 0.1.0
-- Sequence: 0002
-- Idempotent: safe to run multiple times

BEGIN;

-- 1) Ensure schema exists and has proper grants
GRANT USAGE ON SCHEMA api TO app_root;
GRANT CREATE ON SCHEMA api TO app_root;

-- 2) Create webhook_subscriptions table
CREATE TABLE IF NOT EXISTS api.webhook_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID NOT NULL,  -- FK to auth.credentials
    provider VARCHAR(50) NOT NULL,  -- 'ms365' or 'googlews'
    
    -- External subscription details
    external_subscription_id VARCHAR(255) NOT NULL,  -- MS365 subscriptionId or GWS historyId
    resource_path TEXT NOT NULL,  -- e.g., 'me/messages', 'users/{userId}/mailFolders/inbox/messages'
    
    -- Subscription configuration
    notification_url TEXT NOT NULL,  -- Where webhook notifications are sent
    change_types TEXT[],  -- e.g., ['created', 'updated', 'deleted']
    
    -- Lifecycle tracking
    status VARCHAR(50) NOT NULL DEFAULT 'active',  -- active, expired, error
    expires_at TIMESTAMP WITH TIME ZONE,  -- When subscription expires
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_notification_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT fk_credential FOREIGN KEY (credential_id) 
        REFERENCES auth.credentials(id) ON DELETE CASCADE,
    CONSTRAINT unique_subscription UNIQUE (credential_id, external_subscription_id)
);

-- 3) Create indexes
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_credential 
    ON api.webhook_subscriptions(credential_id);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_status 
    ON api.webhook_subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_webhook_subscriptions_expires 
    ON api.webhook_subscriptions(expires_at) WHERE status = 'active';

-- 4) Grant permissions
GRANT ALL PRIVILEGES ON api.webhook_subscriptions TO app_root;

-- 5) Record migration
INSERT INTO api.migration_history (schema_name, file_seq, name, notes)
VALUES ('api', 2, '0002_webhook_subscriptions.sql', 
        'Create webhook_subscriptions table for MS365 and Google Workspace')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- 6) Update schema version in auth.schema_registry
INSERT INTO auth.schema_registry (service, semver, ts_key, applied_at)
VALUES ('api', '0.1.0', EXTRACT(EPOCH FROM NOW()), NOW())
ON CONFLICT (service) DO UPDATE SET
    semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    applied_at = EXCLUDED.applied_at;

-- 7) Record version history
INSERT INTO auth.schema_registry_history (service, semver, ts_key)
VALUES ('api', '0.1.0', EXTRACT(EPOCH FROM NOW()));

COMMIT;
