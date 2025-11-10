# Deploy - Global Docker Infrastructure

This folder contains **global Docker infrastructure** only (not per-service deployment files).

## Structure

- **`traefik/`** - Traefik reverse proxy configuration (shared by all services)
- **`local/`** - Local testing orchestration with Docker Compose
- **`hostinger/`** - Historical reference only (see README in that folder)

## Service Deployment Files

**Each service's VPS deployment file is located in its own folder:**
- `postgres/postgres.compose.yml` - PostgreSQL VPS deployment
- `auth/auth.compose.yml` - Auth Service VPS deployment  
- `webui/webui.compose.yml` - WebUI VPS deployment
- `api/api.compose.yml` - API Service VPS deployment (future)

Deploy each service individually via Hostinger Docker UI by pasting the service's compose file and setting environment variables.

---

# Deploy folder guide

Use the files under `deploy/hostinger/` for copy‑paste into Hostinger Compose. For service projects (API, Auth, Postgres), you can also copy the compose files directly from their folders.

Primary pasteables
- `hostinger/pasteables.md` — n8n environment panel lines and Traefik labels to attach n8n to your existing Traefik network.

Service compose references
- API: `api/api.compose.yml` (private by default; optional public webhook via Traefik labels). Requires `TRAEFIK_NETWORK` and optional `DATABASE_URL`.
- Auth: `auth/auth.compose.yml` (private by default; optional public webhook via Traefik labels). Requires `TRAEFIK_NETWORK` and optional `DATABASE_URL`.
- Postgres: `postgres/postgres.compose.yml` (private-only). Requires `TRAEFIK_NETWORK`. Optional `POSTGRES_BIND_LOCALHOST=true` to bind to 127.0.0.1:5432 for SSH-tunneled admin.

Existing files (reference)
- `hostinger/original-n8n/` — Your original n8n stack (`docker-compose.yml` and `.env`).
- `hostinger/pasteables.md` — Longer guidance (copy‑paste focused) for Hostinger.

Notes
- The Traefik resolver name in labels is `mytlschallenge` to match a TLS‑ALPN challenge setup. Keep it consistent with your Traefik service args.
 - Per-service migrations at startup have been removed for Auth. Apply manual SQL under `auth/migrations/` during deploy. No Alembic stamping is required; API gating uses only `auth.schema_registry.semver`.
