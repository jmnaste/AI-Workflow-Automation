# Alembic in Auth: current status

We’ve pivoted to manual, versioned SQL migrations under `auth/migrations/` as the source of truth. Alembic remains present for compatibility and future use, but the app no longer runs Alembic at startup.

## Why the change
- Repeated deploy friction (schema permissions, version table placement) slowed progress.
- Manual SQL gives explicit, auditable steps and easy verification in constrained hosting.
- We preserve Alembic compatibility by stamping its version table to the current head.

## What’s active now
- Manual migrations live in `auth/migrations/` with numbered files: `0000_…`, `0001_…`, etc.
- A `migration_history` table tracks applied files, checksums, who applied them, and when.
- The Alembic version table `auth.alembic_version_auth` is stamped to the latest known head (currently `20251105_000002`) so Alembic sees the schema as up-to-date.
- `MIGRATE_AT_START` is disabled by default in `auth.compose.yml`.

## Keeping Alembic in sync
If you add a new manual SQL migration and want Alembic to remain aligned:
1) Generate a new Alembic revision with identical DDL changes (optional during manual phase).
2) After applying the manual SQL to the database, stamp Alembic’s version table to that new revision ID.

Stamps can be done with either:
- Running Alembic with `stamp <revision>` against the same DSN and configured version table/schema; or
- Executing `UPDATE auth.alembic_version_auth SET version_num = '<revision_id>';` (ensure the table exists first).

Important: Do not run `alembic upgrade` while manual SQL is the source of truth. Only use `stamp` to align the pointer.

## Switching back to Alembic-driven upgrades later
When ready to return to automatic, app-managed Alembic migrations:
- Ensure the database role has `USAGE, CREATE` on schema `auth` and can write to `auth.alembic_version_auth`.
- Add a new Alembic revision capturing any changes made during the manual period.
- Set `MIGRATE_AT_START=true` for the auth service, deploy, and watch logs for a clean `upgrade head`.
- Keep the manual SQL folder for reference, or retire it once the Alembic revision history fully reflects reality.

## References
- Active manual SQL: `auth/migrations/`
- Alembic config: `auth/alembic.ini` and `auth/alembic/env.py`
- Runtime switch: `MIGRATE_AT_START` in `auth/auth.compose.yml`

If anything diverges, treat `auth/migrations/` as the canonical source and adjust Alembic by stamping to match the live DB state.