# UI Deployment — VPS with Traefik

This guides you to deploy the Vite-built UI as a static SPA served by Nginx behind Traefik. The image is built and published by GitHub Actions to GHCR, and the VPS pulls it on deploy.

## Prerequisites
- Traefik running with an external docker network (e.g., `root_default` or `traefik`)
- DNS A/AAAA record pointing `UI_HOST` to your server
- Environment variables in `.env` used by compose:
  - `TRAEFIK_NETWORK` (e.g., `root_default`)
  - `TRAEFIK_CERT_RESOLVER` (e.g., `letsencrypt`)
  - `UI_HOST` (e.g., `ui.example.com`)

## Deploy (from repo root)

```powershell
# 1) Ensure logo exists
#    Place the logo at images/Flovify-logo.png and generate favicons to images/favicon/

# 2) Compose up the UI (pulls GHCR image; Traefik labels configured)
cd deploy
$env:UI_HOST = "ui.example.com"; docker compose -f ui.compose.yml --env-file .env up -d
```

After a few seconds, Traefik should route https://$UI_HOST to the UI container.

## Quick health endpoint
Verify the container is healthy via a built-in JSON endpoint:

```powershell
curl https://$env:UI_HOST/ui/health
# Expected: {"status":"ok","service":"ui","ts":"<iso>"}
```

## Notes
- The UI container serves static files and proxies same-origin requests to backend services:
  - `/api/` -> `http://api:8000/`
  - `/auth/` -> `http://auth:8000/`
  Ensure `api` and `auth` services are attached to the same Traefik network with those aliases (already done in their compose files).
- If your API lives under a different host, configure CORS on the API and update Vite proxy for local development.
- Nginx config implements SPA fallback to `/index.html`.

## Update Flow
```powershell
# Re-deploy to pull latest GHCR tag (e.g., :main)
cd deploy
docker compose -f ui.compose.yml --env-file .env up -d
```

## Local development (optional)
For a quick local preview behind Nginx:

```powershell
cd ui
docker compose -f local.compose.yml up -d
# Open http://localhost:5173/ui/health
```

Note: The UI proxies /api and /auth to container DNS names (api, auth). For end-to-end local calls, either run API/Auth on the same docker network with matching compose files, or change the Nginx proxy targets to host.docker.internal:PORT for local-only testing.

## Troubleshooting
- 404 for images: ensure `/images/Flovify-logo.png` exists in repo root; favicons under `images/favicon/` should include `favicon-32x32.png` referenced by `ui/index.html`.
- Blank page after deploy: confirm Traefik labels and network in `deploy/ui.compose.yml`. Check container logs: `docker logs webui`.
- Mixed content/CORS: make sure API is served via HTTPS under the same host or allow-list the UI origin in API.
