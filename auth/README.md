# Auth service (private by default, optional public webhook)

A minimal FastAPI-based auth service, mirroring the API project structure. It runs privately on your Traefik Docker network and can optionally expose a narrow public webhook route via Traefik.

## Image

- Name: `ghcr.io/jmnaste/ai-workflow-automation/auth:main`
- Built by: `/.github/workflows/build-auth.yml` on each push to `main` or changes under `auth/`

## Deploy on Hostinger (private service)

1) In Hostinger → Docker → Compose → Create Project
2) Paste YAML from `auth/auth.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
TRAEFIK_NETWORK=root_default
# Optional if using Postgres: DSN on the private Docker network
DATABASE_URL=postgresql://app_system:YOUR_PASSWORD@postgres:5432/app_db
```

4) Deploy. No ports are published and no Traefik router is created; the service runs privately.

### Configure the database DSN (DATABASE_URL)

Set the `DATABASE_URL` in the Hostinger Environment panel for this project. The compose file references it as `${DATABASE_URL}`.

Common formats (psycopg):

- Same Docker network (your own Postgres container):
  - `postgresql://app_system:YOUR_PASSWORD@postgres:5432/app_db`
  - Replace `postgres` with your Postgres service/alias name on the shared network.
  - Optional params: `?connect_timeout=3&application_name=auth`

- Managed/external Postgres (public hostname):
  - `postgresql://USER:PASS@HOST:PORT/DBNAME?sslmode=require&connect_timeout=3&application_name=auth`

Notes:
- URL‑encode special characters in passwords (e.g., `!` → `%21`).
- Prefer private networking between containers; require TLS (`sslmode=require`) across public networks.
- Verify with: `curl -s http://auth:8000/auth/db/health`

## Outbound internet access (egress)

No additional configuration is required for outbound HTTP(S); Docker provides NATed egress by default. Ensure your VPS allows outbound traffic and DNS resolution is working.

Quick checks from inside the network:

- `curl -s http://auth:8000/auth/health`
- `curl -s http://auth:8000/auth/egress/health`
- DB (if configured): `curl -s http://auth:8000/auth/db/health`

## Expose a public webhook (optional)

To receive webhooks from external systems, enable a narrowly scoped Traefik router:

In Hostinger → Edit the project → Environment, add:

```
AUTH_PUBLIC=true
AUTH_WEBHOOK_HOST=webhooks.example.com
AUTH_WEBHOOK_PATH_PREFIX=/webhook
AUTH_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt
```

Redeploy. Traefik will route only requests that match the configured host and path prefix to the auth service on port 8000.

Security tips:
- Use a secret/unpredictable path (e.g., `/webhook/<random-token>`)
- Validate signatures or tokens from the sender
- Optionally add Traefik middlewares (rate limit, IP allowlist, basic auth)

## Database migrations (Alembic)

This service owns the `auth` schema and can apply its migrations automatically at startup.

Environment variables:

Migrations at container startup have been removed. Use the manual, versioned SQL under `auth/migrations/` to apply changes and keep the Alembic version table stamped for compatibility.
- `MIGRATIONS_DATABASE_URL` (optional): if set, overrides `DATABASE_URL` for running migrations.
- `SERVICE_SEMVER` (optional): semver string to record in the registry/history (defaults to the app version `0.1.0`).

Behavior:

On start, the launcher simply starts Uvicorn. Database migrations are not run automatically.
- The Alembic version table is `auth.alembic_version_auth`.
- `auth.schema_registry` records the current service semantic version and Alembic revision applied. A historical log is kept in `auth.schema_registry_history`.

### Inspect versions

- Current and recent versions: `GET /auth/versions?n=5` (reverse chronological)
- Health: `GET /auth/health`

## Troubleshooting

- Service unreachable internally:
  - Confirm both services share the Traefik network (`TRAEFIK_NETWORK`).
  - Verify alias `auth` exists on the network.
- Image not found:
  - Confirm `ghcr.io/jmnaste/ai-workflow-automation/auth:main` exists under GitHub Packages.
- Need a fixed version:
  - Replace `:main` with a commit SHA tag published by the workflow (e.g., `:sha-<short>`).
