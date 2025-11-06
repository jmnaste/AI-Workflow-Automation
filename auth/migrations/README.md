# Manual SQL migrations for Auth

This folder contains hand-written, idempotent SQL migrations for the `auth` schema. Each file:
- Is prefixed with a zero-padded sequence number (e.g., `0001_...`) that defines apply order.
- Ends with an INSERT into `auth.migration_history` to record the migration.
- Uses `IF NOT EXISTS` and `ON CONFLICT` to be safe on re-runs.

## Files
- `0000_init_migration_history.sql` — creates `auth.migration_history` used to log applied migrations.
- `0001_auth_bootstrap.sql` — creates initial schema (users, tenants, …), history, stamps `auth.alembic_version_auth` to `20251105_000002`, and seeds `auth.schema_registry` and `auth.schema_registry_history`.

## How to run

Run on the server against the `app_db` database, in order, one file at a time.

Option A: from the Postgres container (Linux VPS)

```bash
# open psql as an admin for app_db
docker exec -it <postgres_container_name> psql -U app_root -d app_db

-- inside psql, run each file in order (adjust path if you copied files into the container)
\i /app/auth/migrations/0000_init_migration_history.sql
\i /app/auth/migrations/0001_auth_bootstrap.sql
```

Option B: using a temporary client container on the same Docker network

```bash
docker run --rm -it --network root_default -v $(pwd)/auth/migrations:/migs:ro postgres:16-alpine \
  psql "postgresql://db_root:YOUR_PASSWORD@postgres:5432/app_db" -f /migs/0000_init_migration_history.sql

docker run --rm -it --network root_default -v $(pwd)/auth/migrations:/migs:ro postgres:16-alpine \
  psql "postgresql://db_root:YOUR_PASSWORD@postgres:5432/app_db" -f /migs/0001_auth_bootstrap.sql
```

Verification queries:

```sql
-- Should list all Auth tables
\dt auth.*

-- Alembic version should show 20251105_000002
SELECT * FROM auth.alembic_version_auth;

-- Registry pointer and history should have at least one row
SELECT * FROM auth.schema_registry;
SELECT * FROM auth.schema_registry_history ORDER BY id DESC LIMIT 5;

-- Migration history should include files you've just applied
SELECT schema_name, file_seq, name, applied_by, applied_at FROM auth.migration_history ORDER BY file_seq;
```

## Conventions
- New migrations: copy `0001_auth_bootstrap.sql` as a template, increment the number, and put only your changes. End with an INSERT into `auth.migration_history` like:

```sql
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', 2, '0002_add_something.sql', md5('0002_add_something.sql'), 'describe change')
ON CONFLICT (schema_name, file_seq) DO NOTHING;
```

- Keep migrations idempotent when feasible using `IF NOT EXISTS` / `ON CONFLICT`.
- Startup migrations have been removed; the Auth container does not run Alembic on boot. Apply these SQL files explicitly during deploy.
- For every migration, you must update three things:
  1) `auth.alembic_version_auth.version_num` — stamp to the new revision identifier.
  2) `auth.schema_registry` — upsert the current service semver and revision.
  3) `auth.schema_registry_history` — append a row mirroring the registry pointer.

### Required footer for each new migration
Replace the placeholders before applying (SEMVER and REVISION). Use UTC for `ts_key`.

```sql
-- Alembic version stamp (manual)
CREATE TABLE IF NOT EXISTS auth.alembic_version_auth (
    version_num VARCHAR(32) PRIMARY KEY
);
-- Ensure row exists, then set to the new revision
INSERT INTO auth.alembic_version_auth(version_num)
VALUES ('<REVISION>')
ON CONFLICT (version_num) DO NOTHING;
UPDATE auth.alembic_version_auth SET version_num = '<REVISION>';

-- Update registry pointer and history
INSERT INTO auth.schema_registry(service, semver, ts_key, alembic_rev)
VALUES (
  'auth',
  '<SEMVER>',
  to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint,
  '<REVISION>'
)
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    alembic_rev = EXCLUDED.alembic_rev,
    applied_at = now();

INSERT INTO auth.schema_registry_history(service, semver, ts_key, alembic_rev, applied_at)
SELECT service, semver, ts_key, alembic_rev, applied_at
FROM auth.schema_registry
WHERE service = 'auth'
ON CONFLICT DO NOTHING;

-- Record this migration in migration_history (adjust seq/name)
INSERT INTO auth.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('auth', <SEQ>, '<FILENAME>', md5('<FILENAME>'), 'describe change')
ON CONFLICT (schema_name, file_seq) DO NOTHING;
```

Notes:
- For API gating to take effect, set `API_MIN_AUTH_VERSION` in the API service to the minimal semver your API requires. The API compares this to `auth.schema_registry.semver`.
- If you plan to return to Alembic-driven upgrades later, prefer using a real Alembic revision ID for `<REVISION>`. If you use a synthetic value (e.g., `manual_0002_20251106`), you will need to `alembic stamp` back to a real revision before resuming Alembic upgrades.
