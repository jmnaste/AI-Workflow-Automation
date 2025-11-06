-- Manual bootstrap for Auth schema (equivalent to Alembic 000001 + 000002)
-- Idempotent: uses IF NOT EXISTS and ON CONFLICT where applicable

BEGIN;

-- 1) Ensure schema
CREATE SCHEMA IF NOT EXISTS auth;

-- 2) Core tables (from 20251105_000001)
CREATE TABLE IF NOT EXISTS auth.users (
    id uuid PRIMARY KEY,
    phone_e164 text UNIQUE NOT NULL,
    role text NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin','super')),
    is_active boolean NOT NULL DEFAULT true,
    verified_at timestamptz NULL,
    last_login_at timestamptz NULL,
    created_by uuid NULL REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auth.tenants (
    id uuid PRIMARY KEY,
    provider text NOT NULL CHECK (provider IN ('ms365','google','other')),
    external_tenant_id text NOT NULL,
    display_name text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, external_tenant_id)
);

CREATE TABLE IF NOT EXISTS auth.users_tenants (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id uuid NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    tenant_role text NOT NULL DEFAULT 'member' CHECK (tenant_role IN ('owner','admin','member','viewer')),
    created_at timestamptz NOT NULL DEFAULT now(),
    created_by uuid NULL REFERENCES auth.users(id) ON DELETE SET NULL,
    UNIQUE (user_id, tenant_id)
);

CREATE TABLE IF NOT EXISTS auth.settings (
    id uuid PRIMARY KEY,
    scope text NOT NULL DEFAULT 'global' CHECK (scope IN ('global','tenant')),
    scope_id uuid NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    key text NOT NULL,
    value text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (scope, scope_id, key)
);

CREATE TABLE IF NOT EXISTS auth.otp_challenges (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    code_hash bytea NOT NULL,
    expires_at timestamptz NOT NULL,
    attempts int NOT NULL DEFAULT 0,
    max_attempts int NOT NULL DEFAULT 8,
    status text NOT NULL DEFAULT 'sent' CHECK (status IN ('sent','approved','denied','expired','canceled')),
    sent_at timestamptz NOT NULL DEFAULT now(),
    used_at timestamptz NULL,
    request_ip inet NULL,
    user_agent text NULL,
    CHECK (attempts BETWEEN 0 AND max_attempts)
);
CREATE INDEX IF NOT EXISTS idx_otp_user_expires ON auth.otp_challenges (user_id, expires_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS otp_one_active_per_user ON auth.otp_challenges(user_id) WHERE status = 'sent';

CREATE TABLE IF NOT EXISTS auth.sessions (
    id uuid PRIMARY KEY,
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    issued_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    refresh_token_hash bytea NULL,
    device_fingerprint text NULL,
    ip inet NULL,
    revoked_at timestamptz NULL,
    revoked_reason text NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_expires ON auth.sessions (user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON auth.sessions (expires_at);

CREATE TABLE IF NOT EXISTS auth.login_audit (
    id uuid PRIMARY KEY,
    user_id uuid NULL REFERENCES auth.users(id) ON DELETE SET NULL,
    phone_e164 text NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('success','invalid_code','expired','throttled','locked')),
    reason text NULL,
    ip inet NULL,
    user_agent text NULL,
    at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_login_audit_user_at ON auth.login_audit (user_id, at DESC);
CREATE INDEX IF NOT EXISTS idx_login_audit_phone_at ON auth.login_audit (phone_e164, at DESC);

CREATE TABLE IF NOT EXISTS auth.rate_limits (
    id uuid PRIMARY KEY,
    subject_type text NOT NULL CHECK (subject_type IN ('phone','ip')),
    subject text NOT NULL,
    window_start timestamptz NOT NULL,
    window_seconds int NOT NULL,
    count int NOT NULL DEFAULT 0,
    limit_value int NOT NULL,
    UNIQUE (subject_type, subject, window_start, window_seconds)
);

-- Schema registry + history (from 20251105_000001 and 000002)
CREATE TABLE IF NOT EXISTS auth.schema_registry (
    service text PRIMARY KEY,
    semver text NOT NULL,
    ts_key bigint NOT NULL,
    alembic_rev text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auth.schema_registry_history (
    id bigserial PRIMARY KEY,
    service text NOT NULL,
    semver text NOT NULL,
    ts_key bigint NOT NULL,
    alembic_rev text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_schema_registry_history_service_applied_at ON auth.schema_registry_history(service, applied_at DESC);

-- Alembic version stamp (manual)
CREATE TABLE IF NOT EXISTS auth.alembic_version_auth (
    version_num VARCHAR(32) PRIMARY KEY
);
INSERT INTO auth.alembic_version_auth(version_num)
VALUES ('20251105_000002')
ON CONFLICT (version_num) DO NOTHING;

-- Seed pointer and history
INSERT INTO auth.schema_registry(service, semver, ts_key, alembic_rev)
VALUES (
  'auth',
  COALESCE(current_setting('SERVICE_SEMVER', true), '0.1.1'),
  to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint,
  '20251105_000002'
)
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    alembic_rev = EXCLUDED.alembic_rev,
    applied_at = now();

INSERT INTO auth.schema_registry_history(service, semver, ts_key, alembic_rev, applied_at)
SELECT service, semver, ts_key, alembic_rev, applied_at
FROM auth.schema_registry
ON CONFLICT DO NOTHING;

-- Record this migration
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', 1, '0001_auth_bootstrap.sql', md5('0001_auth_bootstrap.sql'), 'manual bootstrap: core tables + history + stamp')
ON CONFLICT (schema_name, file_seq) DO NOTHING;

COMMIT;
