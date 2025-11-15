# API deployment (private by default, optional public webhook)

This folder contains everything needed to build the API image in GitHub Actions and deploy it on Hostinger, attached to your existing Traefik network. By default the API is private (not reachable from the internet); n8n (and other services on the same Docker network) can call it internally as `http://api:8000`. You can optionally expose a narrow public webhook route via Traefik when needed.

## Image

- Name: `ghcr.io/jmnaste/ai-workflow-automation/api:main`
- Built by: `/.github/workflows/build-api.yml` on each push to `main`

## Deploy on Hostinger (private API)

1) In Hostinger → Docker → Compose → Create Project
2) Paste YAML from `api/api.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
TRAEFIK_NETWORK=root_default

# Database connection
DATABASE_URL=postgresql://app_root:YOUR_PASSWORD@postgres:5432/app_db

# Auth service integration (for token vending)
AUTH_SERVICE_URL=http://auth:8000
SERVICE_SECRET=<generate-with-openssl-rand-base64-32>

# Optional: Minimum Auth schema version required to start
API_MIN_AUTH_VERSION=0.2.0
```

4) Deploy. No ports are published and no Traefik router is created; the API runs privately.

### Configure the database DSN (DATABASE_URL)

Set the `DATABASE_URL` in the Hostinger Environment panel for this project. The compose file references it as `${DATABASE_URL}`.

Common formats (psycopg):

- Same Docker network (your own Postgres container):
  - `postgresql://app_root:YOUR_PASSWORD@postgres:5432/app_db`
  - Replace `postgres` with your Postgres service/alias name on the shared network.
  - Optional params: `?connect_timeout=3&application_name=api`

- Managed/external Postgres (public hostname):
  - `postgresql://USER:PASS@HOST:PORT/DBNAME?sslmode=require&connect_timeout=3&application_name=api`

Notes:
- URL‑encode special characters in passwords (e.g., `!` → `%21`).
- Keep DB private on the Docker network whenever possible; use TLS (`sslmode=require`) when crossing the public internet.
- Verify with: `curl -s http://api:8000/api/db/health`

## Outbound internet access (egress)

No additional configuration is required for the API to make outbound HTTP(S) calls to public services; Docker provides NATed egress by default. Ensure your VPS firewall allows outbound traffic and DNS resolution works in your environment.

Quick check from outside (through the API):

- `curl -s "http://api:8000/api/egress/health"` → returns `{"status":"ok","url":"https://example.com","code":200}` when outbound works
- To test a specific endpoint: `curl -s "http://api:8000/api/egress/health?url=https://httpbin.org/status/204"`

## Expose a public webhook (optional)

If you need the API to receive webhooks from external systems, you can enable a narrowly scoped Traefik router that only matches a specific host and path prefix. This keeps the service private by default and only exposes what you intend.

1) In Hostinger → Edit the API project → Environment, add:

```
# Enable public routing via Traefik
API_PUBLIC=true

# Router host and path you control (must match your DNS)
API_WEBHOOK_HOST=webhooks.flovify.ca

# Path prefix for all webhook routes (covers all providers)
API_WEBHOOK_PATH_PREFIX=/webhooks

# Traefik entrypoints (typically websecure for HTTPS)
API_ENTRYPOINTS=websecure

# TLS certificate resolver configured in your Traefik instance
TRAEFIK_CERT_RESOLVER=letsencrypt
```

2) Redeploy the project. Traefik will route requests matching:

- Host: `API_WEBHOOK_HOST`
- Path prefix: `API_WEBHOOK_PATH_PREFIX`

to the API container's port 8000.

**Example public URLs**: 
- MS365: `https://webhooks.flovify.ca/webhooks/ms365/webhook`
- Google: `https://webhooks.flovify.ca/webhooks/googlews/webhook`

**Important**: Use `/webhooks` as the path prefix to expose all webhook receiver routes (`/webhooks/*`) while keeping other API endpoints (`/api/*`) private on the Docker network.

Security tips:

- MS365 webhooks validate the endpoint during subscription creation
- Consider validating an HMAC signature or token header from the webhook sender
- Optionally add Traefik middlewares (rate limit, IP allowlist, basic auth). These can be added as extra `traefik.http.middlewares.*` labels and referenced by the router.

## How n8n calls the API

In an n8n HTTP Request node (with n8n attached to the same Traefik network), use:

- URL: `http://api:8000/api/health`

The hostname `api` works because the compose file sets a network alias `api` on the Traefik network.

## Verify internally (optional)

- From inside the n8n container shell: `curl -s http://api:8000/api/health`
- From a temporary debug container attached to the network: `docker run --rm -it --network root_default curlimages/curl:8.10.1 curl -s http://api:8000/api/health`

If you configured `DATABASE_URL`, you can also check DB connectivity:

- `curl -s http://api:8000/api/db/health`

## Environment Variables Reference

### Required

- **`TRAEFIK_NETWORK`**: Docker network name (e.g., `root_default`)
- **`DATABASE_URL`**: PostgreSQL connection string
- **`AUTH_SERVICE_URL`**: Auth service URL for token vending (e.g., `http://auth:8000`)
- **`SERVICE_SECRET`**: Shared secret for service-to-service authentication (generate with `openssl rand -base64 32`)

### Optional

- **`API_MIN_AUTH_VERSION`**: Minimum Auth schema version required (e.g., `0.1.0`). API will refuse to start until Auth has applied this version or higher.
- **`WEBHOOK_WORKER_INTERVAL`**: Poll interval for webhook worker in seconds (default: `10`)
- **`WEBHOOK_WORKER_BATCH_SIZE`**: Max events processed per worker cycle (default: `10`)
- **`WEBHOOK_MAX_RETRIES`**: Max retry attempts for failed events (default: `3`)
- **`API_PUBLIC`**: Set to `true` to enable public webhook routes via Traefik
- **`API_WEBHOOK_HOST`**: Public hostname for webhooks (e.g., `webhooks.flovify.ca`)
- **`API_WEBHOOK_PATH_PREFIX`**: Path prefix for webhook routes (use `/webhooks` to expose all providers)
- **`API_ENTRYPOINTS`**: Traefik entrypoints (e.g., `websecure`)
- **`TRAEFIK_CERT_RESOLVER`**: TLS certificate resolver name (e.g., `letsencrypt`)

### Generating SERVICE_SECRET

The `SERVICE_SECRET` must match between API and Auth services for token vending to work:

```bash
openssl rand -base64 32
```

Add the same value to both API and Auth environment variables.

## Gate API on Auth schema version

To avoid incompatibilities, set `API_MIN_AUTH_VERSION` to require a minimum Auth schema version.

On startup, the API will query `auth.schema_registry` and require that the `auth` service semver is greater than or equal to `API_MIN_AUTH_VERSION`. If the check fails, the API will exit with an error so your orchestrator restarts it after Auth finishes migrations.

## Troubleshooting

- API unreachable from n8n:
  - Ensure both services are on the same Docker network (value of `TRAEFIK_NETWORK`).
  - Confirm the alias `api` exists: `docker network inspect <network> | jq '.[0].Containers'`.
- Image not found:
  - Confirm `ghcr.io/jmnaste/ai-workflow-automation/api:main` exists under GitHub Packages for this repo.
  - If your registry or namespace differs, edit the `image:` in the compose file accordingly.
- Need a fixed version:
  - Replace `:main` with the commit SHA tag published by the workflow (e.g., `:sha-<short>`).

- Public webhook not reachable:
  - Confirm `API_PUBLIC=true` and `API_WEBHOOK_HOST` are set.
  - Verify your DNS record points `API_WEBHOOK_HOST` to your Traefik entrypoint IP.
  - Ensure the specified `TRAEFIK_CERT_RESOLVER` exists in your Traefik configuration, or remove that label to use a preconfigured TLS setup.

## CI/CD notes

- The workflow logs into GHCR using the repository’s `GITHUB_TOKEN` and publishes tags:
  - `:main`
  - Branch ref tag
  - `:sha-...`
- To trigger manually: GitHub → Actions → Build and publish API image → Run workflow.
