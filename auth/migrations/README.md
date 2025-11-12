# Manual SQL migrations for Auth (no Alembic)

This folder contains hand-written, idempotent SQL migrations for the `auth` schema. Each file:
- Is prefixed with a zero-padded sequence number (e.g., `0001_...`) that defines apply order.
- Ends with an INSERT into `auth.migration_history` to record the migration.
- Uses `IF NOT EXISTS` and `ON CONFLICT` to be safe on re-runs.

## Files
- `0000_init_migration_history.sql` — creates `auth` schema, grants privileges to `app_root` user, and creates `auth.migration_history` table for tracking applied migrations.
- `0001_auth_bootstrap.sql` — creates core tables (users, tenants, settings, OTP challenges, sessions, audit logs, rate limits), creates `auth.schema_registry` and `auth.schema_registry_history` for version tracking.
- `0002_add_email_to_users.sql` — adds `email text NULL` to `auth.users` and a case-insensitive unique index (`lower(email)`) with `WHERE email IS NOT NULL`; updates registry/history.
- `0004_restructure_for_email_primary.sql` — makes `email` NOT NULL (primary identifier), makes `phone` nullable, adds `otp_preference` column (sms/email); updates registry/history.
- `9999_health_check.sql` — minimal, idempotent health check for psql debugging; logs diagnostics to `auth.migration_health_log` and does NOT change `auth.schema_registry`.

## How to run

Run on the server against the `app_db` database, in order, one file at a time.

Option A (recommended): run psql FROM the auth container (it now includes the migration files and psql client). Specify the Postgres host explicitly with `-h postgres` (service name) so psql uses TCP instead of looking for a local socket.

```bash
# Exec into the auth container (replace <auth_container_name>)
docker exec -it <auth_container_name> psql -h postgres -U app_root -d app_db 

-- Inside psql (auth container):
\i /auth/migrations/0000_init_migration_history.sql
\i /auth/migrations/0001_auth_bootstrap.sql
\i /auth/migrations/0002_add_email_to_users.sql
\i /auth/migrations/0004_restructure_for_email_primary.sql
\i /auth/migrations/9999_health_check.sql
```

Option A2: one-shot psql invocation from the auth container (non-interactive):

```bash
docker exec -it <auth_container_name> psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /auth/migrations/0000_init_migration_history.sql
docker exec -it <auth_container_name> psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /auth/migrations/0001_auth_bootstrap.sql
docker exec -it <auth_container_name> psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /auth/migrations/0002_add_email_to_users.sql
docker exec -it <auth_container_name> psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /auth/migrations/0004_restructure_for_email_primary.sql
docker exec -it <auth_container_name> psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /auth/migrations/9999_health_check.sql
```

Why your previous attempt failed: the path `/auth/migrations/...` does not exist inside the **postgres** container; those files are baked into the auth service image. Also, running `psql` without `-h postgres` inside the auth container makes it try a local UNIX socket (which doesn't exist). Use `-h postgres` (service DNS on the shared network), copy files into the postgres container, or mount them.

Note: If your currently running auth image was built before this change, it may not have psql or the migrations folder yet. In that case, either redeploy with the latest image or use Option B/C below.

Option B: copy migrations into the postgres container first (if you prefer to apply from there)

```bash
# Copy files into postgres container under /tmp/migs
docker cp auth/migrations/0000_init_migration_history.sql <postgres_container_name>:/tmp/migs/0000_init_migration_history.sql
docker cp auth/migrations/0001_auth_bootstrap.sql <postgres_container_name>:/tmp/migs/0001_auth_bootstrap.sql

# Enter postgres container
docker exec -it <postgres_container_name> psql -U app_root -d app_db  # socket works here because server runs locally

-- Inside psql:
\i /tmp/migs/0000_init_migration_history.sql
\i /tmp/migs/0001_auth_bootstrap.sql
\i /tmp/migs/0002_add_email_to_users.sql
\i /tmp/migs/0004_restructure_for_email_primary.sql
\i /tmp/migs/9999_health_check.sql
```

Option C: using a temporary client container on the same Docker network (mount host migrations directory) — needs `-h postgres` or a full connection string.

```bash
docker run --rm -it --network root_default -v $(pwd)/auth/migrations:/migs:ro postgres:16-alpine \
  psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /migs/0000_init_migration_history.sql

docker run --rm -it --network root_default -v $(pwd)/auth/migrations:/migs:ro postgres:16-alpine \
  psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /migs/0001_auth_bootstrap.sql

docker run --rm -it --network root_default -v $(pwd)/auth/migrations:/migs:ro postgres:16-alpine \
  psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /migs/0002_add_email_to_users.sql

docker run --rm -it --network root_default -v $(pwd)/auth/migrations:/migs:ro postgres:16-alpine \
  psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /migs/0004_restructure_for_email_primary.sql

docker run --rm -it --network root_default -v $(pwd)/auth/migrations:/migs:ro postgres:16-alpine \
  psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /migs/9999_health_check.sql
```

Verification queries:

```sql
-- Should list all Auth tables
\dt auth.*

-- Registry pointer and history should have at least one row
SELECT * FROM auth.schema_registry;
SELECT * FROM auth.schema_registry_history ORDER BY id DESC LIMIT 5;

-- Registry pointer and history should have at least one row
SELECT * FROM auth.schema_registry;
SELECT * FROM auth.schema_registry_history ORDER BY id DESC LIMIT 5;

-- Migration history should include files you've just applied
SELECT schema_name, file_seq, name, applied_by, applied_at FROM auth.migration_history ORDER BY file_seq;

-- Health log should show at least one row after 9999
SELECT id, note, db, usr, search_path, server_version, applied_at FROM auth.migration_health_log ORDER BY id DESC LIMIT 5;

Notes:
- `9999_health_check.sql` deliberately does NOT modify `auth.schema_registry`. It’s safe to run any time to validate connectivity and the psql path.
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
- For every migration, you must update:
  1) `auth.schema_registry` — upsert the current service semver and timestamp key.
  2) `auth.schema_registry_history` — append a row mirroring the registry pointer (service, semver, ts_key, applied_at).

### Required footer for each new migration
Replace the placeholders before applying (SEMVER). Use UTC for `ts_key`.

```sql
-- Update registry pointer and history (no Alembic)
INSERT INTO auth.schema_registry(service, semver, ts_key)
VALUES (
  'auth',
  '<SEMVER>',
  to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint
)
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    applied_at = now();

INSERT INTO auth.schema_registry_history(service, semver, ts_key, applied_at)
SELECT service, semver, ts_key, applied_at
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
