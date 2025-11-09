# WebUI — AI Workflow Automation Frontend

A React + TypeScript SPA with BFF (Backend for Frontend) pattern, served by Nginx with Traefik routing. The WebUI uses a Hostinger-inspired design with two-level navigation, subtle styling, and card-based layouts.

**Design Reference**: See [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) for complete design guidelines, color palette, and component styling.

## Image

- Name: `ghcr.io/jmnaste/ai-workflow-automation/webui:main`
- Built by: `/.github/workflows/build-webui.yml` on each push to `main` or changes under `webui/**`

## Deploy on Hostinger (public UI via Traefik)

1) In Hostinger → Docker → Compose → Create Project
2) Paste YAML from `webui/webui.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
TRAEFIK_NETWORK=root_default
UI_HOST=console.flovify.ca
UI_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt
NODE_ENV=production
API_BASE_URL=http://api:8000
AUTH_BASE_URL=http://auth:8000
JWT_SECRET=placeholder-until-auth-service-implemented
JWT_COOKIE_NAME=flovify_token
```

**Note:** `JWT_SECRET` is not currently used since authentication is not yet implemented. Use a placeholder value for now. When you implement the Auth service, generate a secure secret:
```bash
openssl rand -base64 32
```
Then use the same secret in both Auth and WebUI services.

4) Deploy. Traefik will route `https://console.flovify.ca` to the WebUI container on port 80.

### Environment Variables Explained

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `TRAEFIK_NETWORK` | Shared Docker network name where Traefik, API, Auth, and WebUI reside | `root_default` |
| `UI_HOST` | Public hostname for the UI (must match your DNS A record) | `console.flovify.ca` |
| `UI_ENTRYPOINTS` | Traefik entrypoint(s) to bind (websecure = HTTPS/443) | `websecure` |
| `TRAEFIK_CERT_RESOLVER` | Traefik cert resolver name for automatic TLS | `letsencrypt` |
| `NODE_ENV` | Runtime environment indicator | `production` |
| `API_BASE_URL` | Internal Docker DNS URL for API service (used by BFF) | `http://api:8000` |
| `AUTH_BASE_URL` | Internal Docker DNS URL for Auth service (used by BFF) | `http://auth:8000` |
| `JWT_SECRET` | Secret key for JWT validation (must match Auth service) | `your-secret-key-change-in-production` |
| `JWT_COOKIE_NAME` | Name of the JWT cookie (must match Auth service) | `flovify_token` |

**Important notes:**

- The SPA is built at CI time and served statically by Nginx. Environment variables are available to the BFF (Express server) at runtime.
- The BFF uses `API_BASE_URL` and `AUTH_BASE_URL` to communicate with backend services via Docker DNS (private network).
- `JWT_SECRET` must match the secret configured in the Auth service for JWT validation.
- The frontend makes API calls to `/bff/*` endpoints only; the BFF mediates all backend communication.

### DNS Configuration

Before deploying, ensure your DNS has an A record pointing `console.flovify.ca` to your Hostinger VPS public IP. Traefik will automatically provision a Let's Encrypt certificate via the ACME HTTP-01 challenge.

## Architecture & Proxying

The WebUI uses a BFF (Backend for Frontend) pattern:

- **Nginx** serves the React SPA and proxies `/bff/*` to Express server on port 3001
- **BFF (Express)** handles all backend communication, JWT validation, and cookie management
- **API and Auth services** are completely private (no direct browser access)

Request flow:
```
Browser → Traefik (TLS) → Nginx (port 80) → BFF (port 3001) → API/Auth (Docker DNS)
```

Nginx routes:
- **`/bff/`** → proxies to `http://localhost:3001/bff/` (Express BFF server)
- **`/ui/health`** → local health endpoint returning `{"status":"ok","service":"ui"}`
- **`/images/`** → serves static assets from `/usr/share/nginx/html/images/`
- **`/*`** → SPA fallback to `index.html` for client-side routing

This design ensures security (backend services hidden), eliminates CORS, and centralizes authentication/authorization in the BFF.

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

The WebUI's BFF (Backend for Frontend) expects these backend services to be available on the same Docker network:

- **`api`** container at `http://api:8000` (BFF proxies to API service)
- **`auth`** container at `http://auth:8000` (BFF proxies to Auth service)

**Important:** API and Auth services are completely private. The browser cannot access them directly. All requests go through the BFF at `/bff/*` endpoints.

Verify internal DNS resolution from the webui container:

```bash
docker exec -it webui wget -qO- http://api:8000/health
docker exec -it webui wget -qO- http://auth:8000/health
```

If these fail, ensure:
- All services (`webui`, `api`, `auth`) are on the same `TRAEFIK_NETWORK`.
- Each service has the correct network alias (`api`, `auth`, `webui`).

## BFF Health Check

The BFF (Express server) runs inside the webui container on port 3001 and is proxied by Nginx at `/bff/*`:

```bash
curl -s https://console.flovify.ca/bff/health
```

Expected response:

```json
{"status":"healthy","service":"bff","timestamp":"2025-11-09T03:25:55.533Z","environment":"production","version":"1.0.0"}
```

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
