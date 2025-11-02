# AI Workflow Automation — Monorepo

This repository hosts the reference implementation and documentation for the AI Workflow Automation practice.

## Layout

- `api/` — FastAPI boundary service (Python)
- `ui/` — Frontend (static or app)
- `deploy/` — Docker Compose and edge config (Traefik), provider-specific subfolders
- `docs/` — All documentation (Inception strategy docs; Communication posts/assets)

No loose files at repo root beyond this README and dotfiles.

## Quick start (single VPS)

See `docs/deploy_single_vps.md` and the sample stack in `deploy/docker-compose.vps.example.yml`. Prefer same-origin routing so the UI calls the API at `/api`.

## Deployment

You can deploy the UI + API alongside an existing Traefik + n8n stack on a single VPS. Two supported paths:

### A) Hostinger (recommended) — attach to existing Traefik

Prereqs
- DNS: point your UI host (for example, `console.example.com`) to the VPS (A/AAAA).
- Your root project already runs Traefik (ports 80/443) with a certresolver named `mytlschallenge`.

Steps (new Compose project called "ui-api")
1) In Hostinger → Docker Manager → Compose → create project `ui-api`.
2) Use ONE of these YAMLs from this repo:
	- Public repo: `deploy/hostinger/ui-api.compose.from-github.yml` (builds UI/API directly from GitHub).
	- Registry images: `deploy/hostinger/ui-api.compose.images.yml` (pulls images from GHCR built by Actions).
3) Environment panel (paste and edit):
	- `PRIMARY_HOST=console.example.com`
	- `UI_HOST=console.example.com`
	- `TRAEFIK_NETWORK=<the Traefik network name from your root project, e.g. root_default>`
4) Deploy. Traefik will request certificates automatically.

Verify
- UI: `https://console.example.com`
- API health: `https://console.example.com/api/health` should return `{ "status": "ok" }`.
 - Combined UI+API health: `https://console.example.com/health` (served by UI, proxies to API).

Notes
- The API is served only under `/api` on the UI host (same‑origin, no CORS). Internally, services can reach it at `http://api:8000` when on the same Docker network.
- If your provider UI doesn’t support remote Git builds, use the GHCR images variant instead (see CI below).

### B) Deploy directly on the VPS (docker compose)

Prereqs
- Docker Engine + Docker Compose Plugin installed on the VPS.
- DNS A/AAAA for your UI host to the VPS.

Steps
1) Clone this repo on the VPS.
2) Review `deploy/docker-compose.vps.example.yml` and set the environment (either via a `.env` file next to the compose or by inlining values):
	- `PRIMARY_HOST`, `UI_HOST` — your UI hostname.
	- Certificates use the resolver `le` in the example. Adjust to your Traefik configuration if different.
3) Bring the stack up (UI + API + Traefik as defined in the example file).

Verify
- UI at your host; API health at `/api/health`.
 - Combined UI+API health at `/health`.

### CI/CD for images (optional but recommended)

When you prefer pulling images instead of building on the VPS/panel:
- The workflow `/.github/workflows/build-ui-api.yml` builds and publishes two images to GHCR:
  - `ghcr.io/<owner>/<repo>/ui:main`
  - `ghcr.io/<owner>/<repo>/api:main`
- It runs automatically on every push to `main`. To roll out in Hostinger, open the `ui-api` project and click Deploy (it will pull the updated `:main` tags).

Hardening tips
- Keep one reverse proxy (Traefik) per host and attach services to its Docker network.
- Avoid exposing the API on a separate public host unless required; prefer `/api` under the UI host.
- Start strict: hold off on HSTS preload/subdomains until the domain is confirmed stable.

### Process summary

- Develop locally; push to `main`.
- GitHub Actions builds/publishes UI and API images to GHCR with the `:main` tag.
- In Hostinger, open the `ui-api` project and click Deploy to pull and restart with the latest images.
- Verify `https://<UI_HOST>/` and `https://<UI_HOST>/api/health`.
- If using the "from GitHub" compose, deploy will rebuild from the repo instead of pulling images; prefer the images variant for faster, reproducible rollouts.

## Indicators and reporting

Public indicators: time-to-feature; first-pass success/quality; AI contribution stability & reliability. p95 latency/resource usage are supporting diagnostics.

## Security posture

Private-by-default APIs, strict CORS if not same-origin, OIDC/JWT for auth, and one reverse proxy (Traefik) per host. See `2. Platform_architecture.md` → API exposure & access model.
