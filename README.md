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

## Indicators and reporting

Public indicators: time-to-feature; first-pass success/quality; AI contribution stability & reliability. p95 latency/resource usage are supporting diagnostics.

## Security posture

Private-by-default APIs, strict CORS if not same-origin, OIDC/JWT for auth, and one reverse proxy (Traefik) per host. See `2. Platform_architecture.md` → API exposure & access model.
