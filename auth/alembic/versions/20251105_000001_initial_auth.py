"""
initial auth schema: users, tenants, users_tenants, settings, otp_challenges, sessions, login_audit, rate_limits, schema_registry

Revision ID: 20251105_000001
Revises: 
Create Date: 2025-11-05 00:01:00
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251105_000001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Ensure schema
    op.execute("CREATE SCHEMA IF NOT EXISTS auth")

    # Users
    op.execute(
        """
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
        )
        """
    )

    # Tenants
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.tenants (
            id uuid PRIMARY KEY,
            provider text NOT NULL CHECK (provider IN ('ms365','google','other')),
            external_tenant_id text NOT NULL,
            display_name text,
            metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (provider, external_tenant_id)
        )
        """
    )

    # Users_Tenants
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.users_tenants (
            id uuid PRIMARY KEY,
            user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            tenant_id uuid NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            tenant_role text NOT NULL DEFAULT 'member' CHECK (tenant_role IN ('owner','admin','member','viewer')),
            created_at timestamptz NOT NULL DEFAULT now(),
            created_by uuid NULL REFERENCES auth.users(id) ON DELETE SET NULL,
            UNIQUE (user_id, tenant_id)
        )
        """
    )

    # Settings
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.settings (
            id uuid PRIMARY KEY,
            scope text NOT NULL DEFAULT 'global' CHECK (scope IN ('global','tenant')),
            scope_id uuid NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            key text NOT NULL,
            value text NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now(),
            UNIQUE (scope, scope_id, key)
        )
        """
    )

    # OTP Challenges
    op.execute(
        """
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
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_otp_user_expires ON auth.otp_challenges (user_id, expires_at DESC)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS otp_one_active_per_user ON auth.otp_challenges(user_id) WHERE status = 'sent'")

    # Sessions
    op.execute(
        """
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
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_expires ON auth.sessions (user_id, expires_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expires ON auth.sessions (expires_at)")

    # Login audit
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.login_audit (
            id uuid PRIMARY KEY,
            user_id uuid NULL REFERENCES auth.users(id) ON DELETE SET NULL,
            phone_e164 text NOT NULL,
            outcome text NOT NULL CHECK (outcome IN ('success','invalid_code','expired','throttled','locked')),
            reason text NULL,
            ip inet NULL,
            user_agent text NULL,
            at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_login_audit_user_at ON auth.login_audit (user_id, at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_login_audit_phone_at ON auth.login_audit (phone_e164, at DESC)")

    # Rate limits
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.rate_limits (
            id uuid PRIMARY KEY,
            subject_type text NOT NULL CHECK (subject_type IN ('phone','ip')),
            subject text NOT NULL,
            window_start timestamptz NOT NULL,
            window_seconds int NOT NULL,
            count int NOT NULL DEFAULT 0,
            limit_value int NOT NULL,
            UNIQUE (subject_type, subject, window_start, window_seconds)
        )
        """
    )

    # Schema registry
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.schema_registry (
            service text PRIMARY KEY,
            semver text NOT NULL,
            ts_key bigint NOT NULL,
            alembic_rev text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # Record initial version
    op.execute(
        """
        INSERT INTO auth.schema_registry(service, semver, ts_key, alembic_rev)
        VALUES ('auth','0.1.0', 202511050001, '20251105_000001')
        ON CONFLICT (service) DO UPDATE SET semver=excluded.semver, ts_key=excluded.ts_key, alembic_rev=excluded.alembic_rev, applied_at=now()
        """
    )


def downgrade() -> None:
    # Drop in reverse (keep schema intact for version table)
    op.execute("DROP TABLE IF EXISTS auth.rate_limits")
    op.execute("DROP INDEX IF EXISTS auth.idx_login_audit_phone_at")
    op.execute("DROP INDEX IF EXISTS auth.idx_login_audit_user_at")
    op.execute("DROP TABLE IF EXISTS auth.login_audit")
    op.execute("DROP INDEX IF EXISTS auth.idx_sessions_expires")
    op.execute("DROP INDEX IF EXISTS auth.idx_sessions_user_expires")
    op.execute("DROP TABLE IF EXISTS auth.sessions")
    op.execute("DROP INDEX IF EXISTS auth.otp_one_active_per_user")
    op.execute("DROP INDEX IF EXISTS auth.idx_otp_user_expires")
    op.execute("DROP TABLE IF EXISTS auth.otp_challenges")
    op.execute("DROP TABLE IF EXISTS auth.settings")
    op.execute("DROP TABLE IF EXISTS auth.users_tenants")
    op.execute("DROP TABLE IF EXISTS auth.tenants")
    op.execute("DROP TABLE IF EXISTS auth.schema_registry")
    op.execute("DROP TABLE IF EXISTS auth.users")
