# Manual SQL migrations for API

This folder contains hand-written, idempotent SQL migrations for the `api` schema. Each file:
- Is prefixed with a zero-padded sequence number (e.g., `0001_...`) that defines apply order.
- Ends with an INSERT into `api.migration_history` to record the migration.
- Uses `IF NOT EXISTS` and `ON CONFLICT` to be safe on re-runs.

## Files
- `0000_init_migration_history.sql` — creates `api.migration_history` used to log applied migrations.
- `0001_api_bootstrap.sql` — creates the minimal `api.settings` table.
 - `9999_health_check.sql` — minimal, idempotent health check for psql debugging; logs diagnostics to `api.migration_health_log` and does NOT change versions.
 - `_TEMPLATE_next_migration.sql` — starter template for future migrations (columns, tables, indexes, backfill pattern).

## How to run

Run on the server against the same database as the app (e.g., `app_db`), in order, one file at a time.

Option A (recommended): run psql FROM the api container (it includes the migration files and psql client). Specify the Postgres host explicitly with `-h postgres` so psql uses TCP.

```bash
# Exec into the api container (replace <api_container_name>)
docker exec -it <api_container_name> psql -h postgres -U app_root -d app_db

-- Inside psql (api container):
\i /api/migrations/0000_init_migration_history.sql
\i /api/migrations/0001_api_bootstrap.sql
\i /api/migrations/9999_health_check.sql
```

Option A2: one-shot psql invocations from the api container (non-interactive):

```bash
docker exec -it <api_container_name> psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /api/migrations/0000_init_migration_history.sql

docker exec -it <api_container_name> psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /api/migrations/0001_api_bootstrap.sql

docker exec -it <api_container_name> psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /api/migrations/9999_health_check.sql
```

Option B: copy migrations into the postgres container first (if you prefer to apply from there)

```bash
# Copy files into postgres container under /tmp/migs
docker cp api/migrations/0000_init_migration_history.sql <postgres_container_name>:/tmp/migs/0000_init_migration_history.sql
docker cp api/migrations/0001_api_bootstrap.sql <postgres_container_name>:/tmp/migs/0001_api_bootstrap.sql

# Enter postgres container
docker exec -it <postgres_container_name> psql -U app_root -d app_db

-- Inside psql:
\i /tmp/migs/0000_init_migration_history.sql
\i /tmp/migs/0001_api_bootstrap.sql
```

Option C: using a temporary client container on the same Docker network (mount host migrations directory)

```bash
docker run --rm -it --network root_default -v $(pwd)/api/migrations:/migs:ro postgres:16-alpine \
  psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /migs/0000_init_migration_history.sql

docker run --rm -it --network root_default -v $(pwd)/api/migrations:/migs:ro postgres:16-alpine \
  psql -h postgres -U app_root -d app_db -v ON_ERROR_STOP=1 -f /migs/0001_api_bootstrap.sql
```

## Verification queries

```sql
-- Should list API tables
\dt api.*

-- Migration history should include files you've just applied
SELECT schema_name, file_seq, name, applied_by, applied_at FROM api.migration_history ORDER BY file_seq;

-- Settings table should exist
SELECT * FROM information_schema.tables WHERE table_schema='api' AND table_name='settings';

-- Health log should show at least one row after 9999
SELECT id, note, db, usr, search_path, server_version, applied_at FROM api.migration_health_log ORDER BY id DESC LIMIT 5;
```

## Conventions
- Preferred: copy `_TEMPLATE_next_migration.sql`, rename to the next sequence (e.g. `0002_add_feature_flag.sql`), and implement only the new DDL plus the footer.
- Alternative: copy `0001_api_bootstrap.sql` if you need a table creation example.
- Every migration must end with an INSERT into `api.migration_history`:

```sql
INSERT INTO api.migration_history(schema_name, file_seq, name, checksum, notes)
VALUES ('api', 2, '0002_add_something.sql', md5('0002_add_something.sql'), 'describe change')
ON CONFLICT (schema_name, file_seq) DO NOTHING;
```

- Keep migrations idempotent when feasible using `IF NOT EXISTS` / `ON CONFLICT`.
- API does not gate on its own schema version yet; gating is currently based on Auth via `API_MIN_AUTH_VERSION`.

### Optional future: API semver registry
If later required (e.g. another service depends on explicit API schema version), add:

```sql
CREATE TABLE IF NOT EXISTS api.schema_registry (
  service text PRIMARY KEY,
  semver text NOT NULL,
  ts_key bigint NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS api.schema_registry_history (
  id bigserial PRIMARY KEY,
  service text NOT NULL,
  semver text NOT NULL,
  ts_key bigint NOT NULL,
  applied_at timestamptz NOT NULL DEFAULT now()
);
```

Then in each migration (after your DDL):

```sql
INSERT INTO api.schema_registry(service, semver, ts_key)
VALUES ('api', '<SEMVER>', to_char(timezone('UTC', now()), 'YYYYMMDDHH24MI')::bigint)
ON CONFLICT (service) DO UPDATE
SET semver = EXCLUDED.semver,
    ts_key = EXCLUDED.ts_key,
    applied_at = now();

INSERT INTO api.schema_registry_history(service, semver, ts_key, applied_at)
SELECT service, semver, ts_key, applied_at FROM api.schema_registry WHERE service='api'
ON CONFLICT DO NOTHING;
```

Only introduce this when a consumer exists; until then it adds noise without benefit.
