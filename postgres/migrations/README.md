# Database migrations (manual SQL only)

This folder contains SQL migrations you can apply to a brand-new database (or incrementally to an existing one). The initial script creates all tables for users, tenants, OTP, sessions, audit, settings, and rate limits.

## Files

- `001_initial.sql` — Base schema (idempotent on empty DB). Requires Postgres extension `pgcrypto` (enabled by the script) for UUID generation.
- `900_cleanup_examples.sql` — Example maintenance queries for retention. Run on a schedule if desired.

## How to apply on Hostinger (containerized Postgres)

Option A — Copy and run inside the container

1) Copy the file into the container

```powershell
# Replace <container_name> with your Postgres container name in Hostinger (e.g., postgres)
docker cp "postgres/migrations/001_initial.sql" <container_name>:/tmp/001_initial.sql
```

2) Execute the script via psql

```powershell
docker exec -i <container_name> psql -U %POSTGRES_USER% -d %POSTGRES_DB% -f /tmp/001_initial.sql
```

Option B — Paste directly in an interactive psql

```powershell
docker exec -it <container_name> psql -U %POSTGRES_USER% -d %POSTGRES_DB%
-- then paste the contents of 001_initial.sql and run
```

Option C — One-liner from host (if file is on your machine and working directory is repo root)

```powershell
# Windows PowerShell; ensure the path is correct and container name is set
type "postgres\migrations\001_initial.sql" | docker exec -i <container_name> psql -U %POSTGRES_USER% -d %POSTGRES_DB%
```

## Verifying

Run these quick checks after applying the initial migration:

```sql
\dt
SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;
SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN (
  'users','tenants','users_tenants','otp_challenges','sessions','login_audit','settings','rate_limits'
);
```

## Retention jobs

Use `900_cleanup_examples.sql` as a starting point. You can:
- Run it manually when needed (docker exec -i ... psql -f /tmp/900_cleanup_examples.sql)
- Schedule with an external cron, CI job, or a lightweight sidecar that runs SQL on a cadence.

## Notes

- The schema uses `gen_random_uuid()` from `pgcrypto` so no app-side UUID requirement.
- LEGACY (Alembic): Earlier docs referenced optionally using Alembic; current approach is purely manual SQL migrations. If reintroducing a migration tool later, generate revisions that match the canonical SQL here.
- The Auth service now manages its own `auth` schema via manual SQL migrations (no Alembic). Use these raw SQL files for initial bootstrap of a fresh Postgres instance or admin maintenance tasks.
- Never commit actual credentials. Set `POSTGRES_USER` and `POSTGRES_DB` via the Hostinger Environment panel.
