# WebUI — AI Workflow Automation Frontend

A React + TypeScript SPA served by Nginx with Traefik routing. The WebUI proxies API and Auth requests through same-origin paths (`/api`, `/auth`) to avoid CORS issues. It runs on your Traefik Docker network and is publicly accessible via Traefik's configured host.

## Image

- Name: `ghcr.io/jmnaste/ai-workflow-automation/webui:main`
- Built by: `/.github/workflows/build-webui.yml` on each push to `main` or changes under `webui/**`

## Deploy on Hostinger (public UI via Traefik)

1) In Hostinger → Docker → Compose → Create Project
2) Paste YAML from `webui/webui.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
TRAEFIK_NETWORK=root_default
UI_HOST=app.yourdomain.com
UI_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt
NODE_ENV=production
API_BASE_PATH=/api
AUTH_BASE_PATH=/auth
```

4) Deploy. Traefik will route `https://app.yourdomain.com` to the WebUI container on port 80.

### Environment Variables Explained

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `TRAEFIK_NETWORK` | Shared Docker network name where Traefik, API, Auth, and WebUI reside | `root_default` |
| `UI_HOST` | Public hostname for the UI (must match your DNS A record) | `app.yourdomain.com` |
| `UI_ENTRYPOINTS` | Traefik entrypoint(s) to bind (websecure = HTTPS/443) | `websecure` |
| `TRAEFIK_CERT_RESOLVER` | Traefik cert resolver name for automatic TLS | `letsencrypt` |
| `NODE_ENV` | Runtime environment indicator | `production` |
| `API_BASE_PATH` | Path prefix for API proxy inside Nginx (same-origin routing) | `/api` |
| `AUTH_BASE_PATH` | Path prefix for Auth proxy inside Nginx (same-origin routing) | `/auth` |

**Important notes:**

- The SPA is built at CI time and served statically by Nginx. Environment variables are available to the container at runtime but **are not injected into the built JavaScript** unless you add a runtime config injection step.
- The current setup uses these envs for documentation/debugging; the UI relies on Nginx proxy rules to route `/api/*` → `http://api:8000/` and `/auth/*` → `http://auth:8000/` via Docker DNS.
- If you need dynamic frontend config (e.g., feature flags, API base URLs), add a runtime injection script or serve a `/config.json` endpoint.

### DNS Configuration

Before deploying, ensure your DNS has an A record pointing `app.yourdomain.com` to your Hostinger VPS public IP. Traefik will automatically provision a Let's Encrypt certificate via the ACME HTTP-01 challenge.

## Architecture & Proxying

The WebUI Nginx configuration proxies backend services through same-origin paths:

- **`/api/`** → proxies to `http://api:8000/` (API service container)
- **`/auth/`** → proxies to `http://auth:8000/` (Auth service container)
- **`/ui/health`** → local health endpoint returning `{"status":"ok","service":"ui"}`
- **`/images/`** → serves static assets from `/usr/share/nginx/html/images/`
- **`/*`** → SPA fallback to `index.html` for client-side routing

This design eliminates CORS and simplifies frontend API calls (relative paths like `fetch('/api/health')`).

## Health Check

After deployment, verify the UI is running:

```bash
curl -s https://app.yourdomain.com/ui/health
```

Expected response:

```json
{"status":"ok","service":"ui","ts":"2025-11-07T12:34:56+00:00"}
```

## Backend Service Requirements

The WebUI expects these backend services to be available on the same Traefik network:

- **`api`** container at `http://api:8000` (for `/api/*` proxying)
- **`auth`** container at `http://auth:8000` (for `/auth/*` proxying)

Verify internal DNS resolution from another container on the network:

```bash
docker exec -it webui curl -s http://api:8000/api/health
docker exec -it webui curl -s http://auth:8000/auth/health
```

If these fail, ensure:
- All services (`webui`, `api`, `auth`) are on the same `TRAEFIK_NETWORK`.
- Each service has the correct network alias (`api`, `auth`, `webui`).

## Optional: Runtime Environment Injection

If you need to inject environment variables into the built SPA at runtime (e.g., dynamic API base URL, feature flags):

1. Create a `config.json.template` with placeholders:
   ```json
   {
     "apiBasePath": "${API_BASE_PATH}",
     "authBasePath": "${AUTH_BASE_PATH}",
     "environment": "${NODE_ENV}"
   }
   ```

2. Add an entrypoint script that runs `envsubst` to generate `/usr/share/nginx/html/config.json`.

3. Update `index.html` to load `/config.json` before bootstrapping React.

4. Modify the Dockerfile to include the entrypoint.

For now, the WebUI uses build-time defaults and relies on Nginx proxying for backend access.

## Troubleshooting

### Service unreachable or 502 Bad Gateway

- **Check Traefik network:**
  - Verify `TRAEFIK_NETWORK` matches the actual network name:
    ```bash
    docker network ls | grep traefik
    ```
  - Ensure all services (webui, api, auth, traefik) are on the same network.

- **Check backend services:**
  - Verify `api` and `auth` containers are running:
    ```bash
    docker ps | grep -E 'api|auth'
    ```
  - Test internal DNS from webui container:
    ```bash
    docker exec -it webui curl -s http://api:8000/api/health
    docker exec -it webui curl -s http://auth:8000/auth/health
    ```

- **Check Traefik logs:**
  - Look for routing or certificate errors:
    ```bash
    docker logs traefik | grep webui
    ```

### UI loads but API calls fail (CORS or 404)

- **Verify Nginx proxy config:**
  - Ensure `/api/` and `/auth/` proxy rules are present in `webui/nginx.conf`.
  - Restart the webui container after any config changes.

- **Check browser dev tools:**
  - Open Network tab and look for failed requests.
  - Verify requests are going to same-origin paths (`/api/...`, not `http://api:8000/...`).

### Image not found or pull error

- Confirm `ghcr.io/jmnaste/ai-workflow-automation/webui:main` exists under GitHub Packages:
  - Visit: https://github.com/jmnaste/AI-Workflow-Automation/pkgs/container/ai-workflow-automation%2Fwebui

- If using a private repository, ensure Hostinger has GHCR read access:
  - Create a GitHub Personal Access Token (PAT) with `read:packages` scope.
  - Docker login on Hostinger:
    ```bash
    echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
    ```

### Need a specific image version

Replace `:main` with a commit SHA tag published by the workflow:

```yaml
image: ghcr.io/jmnaste/ai-workflow-automation/webui:sha-abc1234
```

GitHub Actions workflow tags each build with the short commit SHA.

## Local Development Preview

For local development, use `webui/local.compose.yml` instead:

```bash
cd webui
docker compose -f local.compose.yml up --build
```

Access at: `http://localhost:5173`

The local compose builds from source, mounts volumes for rapid iteration, and uses a different container name (`webui-local`) to avoid conflicts with VPS deployment.

## Security Notes

- **TLS enforced:** Traefik automatically provisions Let's Encrypt certificates.
- **Same-origin API calls:** Eliminates CORS attack surface.
- **No exposed ports:** Nginx listens on port 80 inside the container; Traefik handles external routing.
- **Static SPA:** No server-side logic or secrets in the UI container.

For production hardening:

- Enable Traefik middlewares: rate limiting, security headers, IP allowlist.
- Use Content Security Policy (CSP) headers in Nginx.
- Regularly update the base image and dependencies.

## Next Steps

After successful deployment:

1. Verify health: `curl -s https://app.yourdomain.com/ui/health`
2. Test API proxy: `curl -s https://app.yourdomain.com/api/health`
3. Test Auth proxy: `curl -s https://app.yourdomain.com/auth/health`
4. Open browser: `https://app.yourdomain.com`

If all checks pass, your WebUI is live and ready to use!

---

## Stack & Architecture (Reference)

### Tech Stack
- **Language/runtime:** TypeScript + React 18
- **Dev server/build:** Vite
- **UI library:** Material UI (MUI) v6 with theme overrides for brand
- **Data fetching/cache:** TanStack Query
- **Routing:** React Router (v7+)
- **Forms & validation:** React Hook Form + Zod
- **Auth:** OIDC Authorization Code + PKCE (oidc-client-ts) against our Auth service
- **HTTP client:** fetch with a thin wrapper + interceptors; OpenAPI types via openapi-typescript (generated)
- **State beyond server cache:** minimal global state via Zustand (only where truly needed)
- **Charts:** Apache ECharts
- **Icons:** Material Icons
- **Brand assets:** `images/Flovify-logo.png` (primary logo), future favicon set under `images/favicon/`
- **Testing:** Vitest + Testing Library (unit) + Playwright (e2e)
- **Lint/format:** ESLint (typescript-eslint) + Prettier; TS strict

### Design Principles
- **Emulation-first:** Use MUI to emulate a familiar, high-quality SaaS UI instead of building from scratch.
- **Speed-to-value:** Prioritize proven components and patterns for rapid delivery.
- **Same-origin access:** API and Auth calls through Traefik/Nginx proxies (`/api`, `/auth`) to eliminate CORS complexity.
- **Authentication:** OIDC flows with tokens stored in memory; refresh handled by oidc-client-ts.

### Initial UX Primitives
- App shell with sidebar + topbar, responsive.
- Pages: Health, Workflow Run Management (list + detail), Metrics (charts), Settings.
- Reusable widgets: Status chips, DataGrid, KPI cards, Code/JSON viewer.
