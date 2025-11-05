# AI Workflow Automation — Monorepo

This repository hosts the reference implementation and documentation for the AI Workflow Automation practice.

## Layout

- `api/` — FastAPI boundary service (Python)
- `auth/` — Auth service (Python), owns the `auth` schema and migrations (Alembic)
- `postgres/` — Private Postgres container project + admin/migrations docs
- `netshell/` — Minimal network shell container for private debugging
- `deploy/` — Docker Compose and edge config (Traefik), provider-specific subfolders
- `docs/` — All documentation (Inception strategy docs; Communication posts/assets)
- `project/` — Conversation logs and working notes

No loose files at repo root beyond this README and dotfiles.

## Development

Run the API locally:

- Entrypoint: `app.main:app`
- Default port: `8000`
- Health: `GET /api/health` → `{ "status": "ok" }`

Example (from a virtualenv):

```bash
pip install -r api/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Deployment

If you’re running n8n behind Traefik on Hostinger, use the n8n labels and environment pasteables in `deploy/hostinger/pasteables.md`.

Service Compose files (copy into Hostinger → Compose → Create Project):
- API: `api/api.compose.yml` (private by default; optional webhook exposure via Traefik labels)
- Auth: `auth/auth.compose.yml` (private by default; optional webhook exposure via Traefik labels)
- Postgres: `postgres/postgres.compose.yml` (private-only; optional localhost bind for SSH-tunneled admin)

Per-service database migrations:
- Auth manages its own `auth` schema via Alembic; to auto-run on container start, set `MIGRATE_AT_START=true` and provide `DATABASE_URL`.
- API can gate startup on Auth’s schema readiness by setting `API_MIN_AUTH_VERSION` (e.g., `0.1.0`).

## CI/CD

Build status

[![Build API](https://github.com/jmnaste/AI-Workflow-Automation/actions/workflows/build-api.yml/badge.svg)](https://github.com/jmnaste/AI-Workflow-Automation/actions/workflows/build-api.yml)
[![Build NetShell](https://github.com/jmnaste/AI-Workflow-Automation/actions/workflows/build-netshell.yml/badge.svg)](https://github.com/jmnaste/AI-Workflow-Automation/actions/workflows/build-netshell.yml)
[![Build Auth](https://github.com/jmnaste/AI-Workflow-Automation/actions/workflows/build-auth.yml/badge.svg)](https://github.com/jmnaste/AI-Workflow-Automation/actions/workflows/build-auth.yml)

Workflows

- `/.github/workflows/build-api.yml` — builds and publishes the API image to GHCR as `ghcr.io/jmnaste/ai-workflow-automation/api` (tags: main, branch, sha).
- `/.github/workflows/build-auth.yml` — builds and publishes the Auth image to GHCR as `ghcr.io/jmnaste/ai-workflow-automation/auth` (tags: main, branch, sha).
- `/.github/workflows/build-netshell.yml` — builds and publishes the NetShell image to GHCR as `ghcr.io/jmnaste/ai-workflow-automation/netshell` (tags: main, branch, sha).

Each workflow writes a job summary with published tags and image digest for quick visibility in the Actions UI.

Package visibility (GHCR)

- Container packages live under GitHub Packages for this repo. If you need them publicly pullable, set the package visibility to Public in GitHub → Packages → [select package] → Package settings.

## Security posture

Private-by-default APIs, strict CORS where applicable, OIDC/JWT for auth, and one reverse proxy (Traefik) per host.
