-- 001_initial.sql
-- Schema bootstrap for OTP login and multi-tenant auth
-- Safe to run on a new empty database. Uses pgcrypto for UUID generation.

BEGIN;

CREATE EXTENSION IF NOT EXISTS "pgcrypto"; -- for gen_random_uuid()

-- USERS
CREATE TABLE IF NOT EXISTS users (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_e164         text UNIQUE NOT NULL,
    role               text NOT NULL DEFAULT 'user' CHECK (role IN ('user','admin','super')),
    is_active          boolean NOT NULL DEFAULT true,
    verified_at        timestamptz NULL,
    last_login_at      timestamptz NULL,
    created_by         uuid NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- TENANTS
CREATE TABLE IF NOT EXISTS tenants (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider            text NOT NULL CHECK (provider IN ('ms365','google','other')),
    external_tenant_id  text NOT NULL,
    display_name        text,
    metadata            jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    UNIQUE (provider, external_tenant_id)
);

-- USERS_TENANTS association (many-to-many)
CREATE TABLE IF NOT EXISTS users_tenants (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id     uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tenant_role   text NOT NULL DEFAULT 'member' CHECK (tenant_role IN ('owner','admin','member','viewer')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    created_by    uuid NULL REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE (user_id, tenant_id)
);

-- SETTINGS (global or per-tenant key-value)
CREATE TABLE IF NOT EXISTS settings (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    scope      text NOT NULL DEFAULT 'global' CHECK (scope IN ('global','tenant')),
    scope_id   uuid NULL REFERENCES tenants(id) ON DELETE CASCADE,
    key        text NOT NULL,
    value      text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (scope, scope_id, key)
);

-- OTP CHALLENGES
CREATE TABLE IF NOT EXISTS otp_challenges (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash     bytea NOT NULL,
    expires_at    timestamptz NOT NULL,
    attempts      int NOT NULL DEFAULT 0,
    max_attempts  int NOT NULL DEFAULT 8,
    status        text NOT NULL DEFAULT 'sent' CHECK (status IN ('sent','approved','denied','expired','canceled')),
    sent_at       timestamptz NOT NULL DEFAULT now(),
    used_at       timestamptz NULL,
    request_ip    inet NULL,
    user_agent    text NULL,
    CHECK (attempts BETWEEN 0 AND max_attempts)
);

-- Indexes and partial constraints for OTP
CREATE INDEX IF NOT EXISTS idx_otp_user_expires ON otp_challenges (user_id, expires_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS otp_one_active_per_user ON otp_challenges(user_id) WHERE status = 'sent';

-- SESSIONS
CREATE TABLE IF NOT EXISTS sessions (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    issued_at           timestamptz NOT NULL DEFAULT now(),
    expires_at          timestamptz NOT NULL,
    refresh_token_hash  bytea NULL,
    device_fingerprint  text NULL,
    ip                  inet NULL,
    revoked_at          timestamptz NULL,
    revoked_reason      text NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_expires ON sessions (user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions (expires_at);

-- LOGIN AUDIT (optional but useful)
CREATE TABLE IF NOT EXISTS login_audit (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NULL REFERENCES users(id) ON DELETE SET NULL,
    phone_e164  text NOT NULL,
    outcome     text NOT NULL CHECK (outcome IN ('success','invalid_code','expired','throttled','locked')),
    reason      text NULL,
    ip          inet NULL,
    user_agent  text NULL,
    at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_login_audit_user_at ON login_audit (user_id, at DESC);
CREATE INDEX IF NOT EXISTS idx_login_audit_phone_at ON login_audit (phone_e164, at DESC);

-- RATE LIMITS (DB-based fallback; Redis preferred for production)
CREATE TABLE IF NOT EXISTS rate_limits (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_type  text NOT NULL CHECK (subject_type IN ('phone','ip')),
    subject       text NOT NULL,
    window_start  timestamptz NOT NULL,
    window_seconds int NOT NULL,
    count         int NOT NULL DEFAULT 0,
    limit_value   int NOT NULL,
    UNIQUE (subject_type, subject, window_start, window_seconds)
);

COMMIT;
