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
 - Per-service migrations at startup have been removed for Auth. Apply manual SQL under `auth/migrations/` during deploy, and keep the Alembic version table stamped to the matching head so API gating via `API_MIN_AUTH_VERSION` remains effective.
