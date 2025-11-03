# AI Workflow Automation — Monorepo

This repository hosts the reference implementation and documentation for the AI Workflow Automation practice.

## Layout

- `api/` — FastAPI boundary service (Python)
- `deploy/` — Docker Compose and edge config (Traefik), provider-specific subfolders
- `docs/` — All documentation (Inception strategy docs; Communication posts/assets)

No loose files at repo root beyond this README and dotfiles.

## Development

Run the API locally (no UI component):

- Entrypoint: `app.main:app`
- Default port: `8000`
- Health: `GET /api/health` → `{ "status": "ok" }`

Example (from a virtualenv):

```bash
pip install -r api/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Deployment

If you’re running n8n behind Traefik on Hostinger, use the n8n labels and environment pasteables in `deploy/hostinger/pasteables.md`. The API can be deployed separately as needed; this repo no longer includes a UI or Nginx configuration.

## CI/CD

The workflow `/.github/workflows/build-api.yml` (or `build-ui-api.yml` with only the API job if retained) builds and publishes the API image to GHCR as `ghcr.io/<owner>/<repo>/api:main` on pushes to `main`.

## Security posture

Private-by-default APIs, strict CORS where applicable, OIDC/JWT for auth, and one reverse proxy (Traefik) per host.
