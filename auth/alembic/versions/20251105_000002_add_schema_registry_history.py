"""
add schema_registry_history table and seed from current registry

Revision ID: 20251105_000002
Revises: 20251105_000001
Create Date: 2025-11-05 00:20:00
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251105_000002'
down_revision = '20251105_000001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.schema_registry_history (
            id bigserial PRIMARY KEY,
            service text NOT NULL,
            semver text NOT NULL,
            ts_key bigint NOT NULL,
            alembic_rev text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    # Helpful index for reverse-chronological queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_schema_registry_history_service_applied_at ON auth.schema_registry_history(service, applied_at DESC)"
    )
    # Seed from current pointer if present
    op.execute(
        """
        INSERT INTO auth.schema_registry_history(service, semver, ts_key, alembic_rev, applied_at)
        SELECT service, semver, ts_key, alembic_rev, applied_at
        FROM auth.schema_registry
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS auth.idx_schema_registry_history_service_applied_at")
    op.execute("DROP TABLE IF EXISTS auth.schema_registry_history")
