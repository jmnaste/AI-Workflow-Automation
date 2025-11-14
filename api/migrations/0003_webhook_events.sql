-- Migration: Webhook Events Tracking
-- Purpose: Store incoming webhook notifications for idempotency and processing
-- Schema: api
-- Version: 0.1.1
-- Sequence: 0003
-- Idempotent: safe to run multiple times

BEGIN;

-- 1) Ensure schema exists and has proper grants
GRANT USAGE ON SCHEMA api TO app_root;
GRANT CREATE ON SCHEMA api TO app_root;

-- 2) Create webhook_events table
CREATE TABLE IF NOT EXISTS api.webhook_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID NOT NULL,  -- FK to auth.credentials
    subscription_id UUID NOT NULL,  -- FK to webhook_subscriptions
    
    -- Event identification
    provider VARCHAR(50) NOT NULL,  -- 'ms365' or 'googlews'
    event_type VARCHAR(100) NOT NULL,  -- 'message.created', 'message.updated', etc.
    
    -- Idempotency tracking
    idempotency_key VARCHAR(500) NOT NULL UNIQUE,  -- credential_id + subscriptionId + resourceId
    external_resource_id VARCHAR(255) NOT NULL,  -- Message ID, file ID, etc.
    
    -- Event payload
    raw_payload JSONB NOT NULL,  -- Full webhook notification
    normalized_payload JSONB,  -- Standardized event format
    
    -- Processing status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    processed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Metadata
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_credential FOREIGN KEY (credential_id) 
        REFERENCES auth.credentials(id) ON DELETE CASCADE,
    CONSTRAINT fk_subscription FOREIGN KEY (subscription_id) 
        REFERENCES api.webhook_subscriptions(id) ON DELETE CASCADE
);

-- 3) Create indexes
CREATE INDEX IF NOT EXISTS idx_webhook_events_credential 
    ON api.webhook_events(credential_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_subscription 
    ON api.webhook_events(subscription_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_status 
    ON api.webhook_events(status) WHERE status IN ('pending', 'failed');
CREATE INDEX IF NOT EXISTS idx_webhook_events_external_resource 
    ON api.webhook_events(external_resource_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_received 
    ON api.webhook_events(received_at);

-- 4) Grant permissions
GRANT ALL PRIVILEGES ON api.webhook_events TO app_root;

-- 5) Record migration
INSERT INTO api.migration_history (schema_name, file_seq, name, notes)
VALUES ('api', 3, '0003_webhook_events.sql', 
        'Create webhook_events table for idempotency and processing tracking')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

-- 6) Update schema version in auth.schema_registry
INSERT INTO auth.schema_registry (service, semver, ts_key, applied_at)
VALUES ('api', '0.1.1', EXTRACT(EPOCH FROM NOW()), NOW())
ON CONFLICT (service) DO UPDATE SET
    semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    applied_at = EXCLUDED.applied_at;

-- 7) Record version history
INSERT INTO auth.schema_registry_history (service, semver, ts_key)
VALUES ('api', '0.1.1', EXTRACT(EPOCH FROM NOW()));

COMMIT;
