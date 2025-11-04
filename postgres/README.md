# PostgreSQL container project (private-only)

A dedicated Postgres service running privately on your VPS. It does not expose any ports and is not routed by Traefik. Other containers on the same external Docker network can reach it at the hostname `postgres` on port `5432`.

- Image: `postgres:16-alpine`
- Data path: persistent named volume (`pgdata`)
- Network: attaches to your Traefik external Docker network for service discovery

## Manual deployment on Hostinger (first deploy)

1) Hostinger → Docker → Compose → Create Project (name it `postgres`)
2) Paste YAML from `postgres/postgres.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
POSTGRES_DB=app_db
POSTGRES_USER=app_root
POSTGRES_PASSWORD=ChangeThis_Strong_And_Long
TRAEFIK_NETWORK=root_default
```

4) Deploy. The `postgres` container will initialize the database and store its data in a persistent named volume.

Notes
- The first startup may take ~10–20s while the cluster initializes.
- Do not expose ports; connectivity is internal-only via Docker network name `postgres`.

## Manual — subsequent deploys/updates

- Redeploy the project to apply changes. Data persists in the `pgdata` named volume.
- To reset the database, stop the project, delete the `pgdata` volume (in Hostinger UI), then redeploy (this wipes all data!).

## Connect from other containers (API, n8n)

Use the service hostname `postgres` and port `5432`. Example DSNs:

- SQLAlchemy/psycopg3 (FastAPI):
  - `postgresql+psycopg://app_user:ChangeThis_Strong_And_Long@postgres:5432/app_db`
- Generic Postgres URL:
  - `postgresql://app_user:ChangeThis_Strong_And_Long@postgres:5432/app_db`

In the API, set an environment variable like:

```
DATABASE_URL=postgresql+psycopg://app_user:ChangeThis_Strong_And_Long@postgres:5432/app_db
```

Ensure the API project is attached to the same external network (`${TRAEFIK_NETWORK}`) so DNS resolves.

## Basic admin commands

Open a psql shell:

```bash
# Replace <container_id_or_name> with the postgres container name from Hostinger
# Default db/user values below use the environment panel settings

docker exec -it <container_id_or_name> psql -U app_user -d app_db
```

Create a simple table (example):

```sql
CREATE TABLE IF NOT EXISTS demo (id serial PRIMARY KEY, note text NOT NULL);
INSERT INTO demo (note) VALUES ('hello');
SELECT * FROM demo;
```

Backup (portable custom format) and copy to host:

```bash
# Create a dump inside the container
docker exec -t <container_id_or_name> pg_dump -U app_user -d app_db -F c -f /tmp/backup.dump
# Copy it out
docker cp <container_id_or_name>:/tmp/backup.dump ./backup.dump
```

Restore (dangerous: overwrites objects):

```bash
# Copy dump back into the container
docker cp ./backup.dump <container_id_or_name>:/tmp/backup.dump
# Restore into the same database
docker exec -t <container_id_or_name> pg_restore -U app_user -d app_db --clean --if-exists /tmp/backup.dump
```

## Security recommendations

- Keep `traefik.enable=false` and avoid publishing ports.
- Use a strong, unique `POSTGRES_PASSWORD` and rotate it periodically.
- Restrict app roles: create a dedicated application role with least privileges if needed.
- Prefer internal DNS `postgres` over exposing the DB to the internet.

## Troubleshooting

- API can’t connect (Name or service not known): both services must share the same external Docker network (`${TRAEFIK_NETWORK}`).
- Authentication failed: verify user, password, and DB name are identical across env and client URL.
- Container restarts repeatedly on first boot: check logs; if you changed env names after first run, you may need to wipe the volume to reinitialize.
