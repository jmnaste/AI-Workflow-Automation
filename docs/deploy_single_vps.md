# Deploying FastAPI API and Frontend UI on the same VPS as n8n (Docker Compose)

This guide shows how to run the API (FastAPI), the UI, and n8n on a single VPS with Docker Compose behind a reverse proxy (Traefik) with automatic HTTPS.

## Prerequisites

- VPS where n8n already runs (e.g., Hostinger). Root/SSH access.
- Docker and Docker Compose installed on the VPS.
- Domains/subdomains and DNS A records pointing to the VPS public IP.
  - Examples used here:
    - UI: `app.example.com`
    - API: `api.example.com` (optional to expose; you can keep API private)
    - n8n: `n8n.example.com` (optional)
- An email address for Let’s Encrypt (for TLS certificates).
- Optional: Managed Postgres (recommended) or an existing Postgres instance.

## Design choices

- Reverse proxy terminates TLS and routes traffic to containers via labels.
- Private Docker network connects `ui`, `api`, and `n8n`. The API can be internal-only (no public router).
- Prefer same-origin to avoid CORS: either:
  - Serve UI at `app.example.com` and proxy `/api` to the API, or
  - Expose both `app.example.com` and `api.example.com` and configure CORS allow-list to the UI origin only.

## Directory layout

```
AI-Workflow-Automation/
  deploy/
    docker-compose.vps.example.yml
    traefik/
      traefik.yml
```

## Environment variables

Create a `.env` (next to the compose file) on the VPS with values like:

```
TRAEFIK_EMAIL=ops@example.com
UI_HOST=app.example.com
API_HOST=api.example.com
N8N_HOST=n8n.example.com
# Optional if you want a single host with /api path
PRIMARY_HOST=app.example.com
```

## Bring-up flow

1. Copy `deploy/docker-compose.vps.example.yml` and `deploy/traefik/traefik.yml` to the VPS.
2. Create the `.env` file with your domains and email.
3. Start the stack with Docker Compose. Traefik will obtain TLS certificates from Let’s Encrypt.
4. Verify:
   - UI resolves and loads over HTTPS
   - API reachable from UI (same origin or via CORS allow-list)
   - n8n reaches API using the internal service name `api:8000` on the Docker network
5. Lock down the host firewall (allow 80/443/SSH, block others). Ensure API container has no published host ports if kept private.

## Security checklist

- API private by default: do not publish host ports; omit public router labels if you don’t need direct internet access.
- If exposing API:
  - Enable OIDC/JWT auth; enforce scopes per route.
  - CORS allow-list to the UI origin only; no wildcard when credentials are used.
- Traefik edge: enable HSTS, set reasonable timeouts, request/body size limits, rate limiting (Traefik or at API).
- Secrets: mount via env files or use a secrets manager; never commit credentials.
- Disable Swagger/Redoc in production or gate behind auth.

## n8n integration

- In n8n HTTP Request nodes, target the API by its internal DNS name: `http://api:8000/...` (no public egress needed).
- If n8n runs outside Docker on the same host, you can publish the API on `127.0.0.1:8000` to keep it local-only, while Traefik still fronts the UI publicly.

## Variants

- Single host with path routing (no separate API domain):
  - Route `https://app.example.com/api` → `api` service; UI calls `/api/...` (same origin, zero CORS).
- Separate hosts (UI and API):
  - Set `UI_HOST` and `API_HOST` and configure CORS.

## Troubleshooting

- Certificates not issued: check DNS propagation and that ports 80/443 are open to the VPS.
- 404 from Traefik: verify service labels/routers and host rules match your domains.
- UI can’t call API: CORS misconfig or wrong base URL; prefer same-origin `/api` routing.

## What this guide does not do

- Provision Postgres/S3; use managed services where possible.
- Configure OIDC/JWT; integrate with your chosen IdP (Auth0/Okta/Azure AD) in the API.

---

For a quick start, see `deploy/docker-compose.vps.example.yml` and adjust image names, domains, and volumes to your setup.
