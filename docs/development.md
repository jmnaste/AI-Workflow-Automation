# Development stack

This repo ships a minimal UI + API setup designed for same‑origin routing in production and a simple local dev loop.

## Tech overview

- API
  - Python 3.12, FastAPI, Uvicorn
  - Entrypoint: `app.main:app`
  - Default port (in container): `8000`
  - Health: `GET /api/health` → `{ "status": "ok" }`
- UI
  - Nginx serving static assets in `ui/static/`
  - Proxies all `/api/*` requests to the API over Docker’s internal network
  - Default port (in container): `80`

## Local development (recommended)

Use the dev compose stack (no Traefik required). The API is private; UI is mapped to your localhost.

```bash
# From repo root
docker compose -f deploy/docker-compose.dev.yml up --build
```

Then open:
- UI: http://localhost:8080
- API health via UI proxy: http://localhost:8080/api/health

If you prefer a first-class React/TypeScript experience with HMR, use the Vite dev server as described in `docs/ui-dev-stack.md`. In that flow, the UI runs on http://localhost:5173 and proxies `/api` to your API.

### UI dev specifics

- The dev stack uses `ui/nginx.dev.conf`, which disables caching so your HTML/CSS/JS edits appear on refresh.
- Static files in `ui/static/` and the Nginx config are bind-mounted; no rebuild needed for content changes.
- If you change `nginx.dev.conf`, restart the `ui` container to reload the config.

### Hot reload

- API: The dev stack runs `uvicorn --reload` and mounts `api/app/` into the container, so code changes are picked up instantly.
- UI: `ui/static/` and `ui/nginx.conf` are bind‑mounted; edits are served immediately (Nginx doesn’t need a reload for static files; config changes require a container restart).

## Alternative dev modes (optional)

- Pure host Python:
  - Create a venv, `pip install -r api/requirements.txt`, then run:
    - `uvicorn app.main:app --reload --port 8001`
  - Adjust the UI upstream to `host.docker.internal:8001` with a temporary `nginx.conf` override if you want the UI container to proxy to your host process.

- Public edge simulation:
  - If you want to test Traefik locally, use the VPS example in `deploy/docker-compose.vps.example.yml` and adapt hosts to `localhost` or your dev domain.

## Contracts and endpoints

- UI serves the SPA and proxies `/api/*` to the API; no public API port in dev by default.
- Health: `/api/health` returns `{ "status": "ok" }`.
- Error modes:
  - If UI shows 502 for `/api/*`, ensure the API container is up and the dev compose is running.
  - CORS is a non‑issue in same‑origin mode; if you bypass the UI and call the API directly from a browser, you may hit CORS.

## Notes

- Production keeps the same pattern: UI as the only public service; API private on the Docker network. Traefik terminates TLS and routes only to the UI.
- For internal automation (e.g., n8n), call the API via `http://api:8000` when attached to the same network, or use the public `/api/*` path via the UI host.
