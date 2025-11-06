# Development

This repository ships headless services (no UI): API, Auth, and Postgres container configuration. Traefik is assumed to run separately as the reverse proxy on your host.

## API (FastAPI)

- Python 3.12, FastAPI, Uvicorn
- Entrypoint: `app.main:app`
- Default port: `8000`
- Health: `GET /api/health` → `{ "status": "ok" }`

### Run API locally

```powershell
pip install -r api/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Optional DB env for health checks:

```powershell
$env:DATABASE_URL="postgresql://app_system:PASS@localhost:5432/app_db"
```

Optional gating on Auth schema (if DB available):

```powershell
$env:API_MIN_AUTH_VERSION="0.1.0"
```

## Auth (FastAPI)

- Owns the `auth` schema and manages migrations via Alembic
- Entrypoint: Python launcher that can run migrations then start Uvicorn
- Default port: `8000`
- Health: `GET /auth/health`

### Run Auth locally (with optional auto-migrations)

```powershell
pip install -r auth/requirements.txt

# If you want migrations at start (requires a running Postgres and DSN):
# Startup migrations have been removed; use the manual SQL in auth/migrations and stamp Alembic if needed.
$env:DATABASE_URL="postgresql://app_system:PASS@localhost:5432/app_db"

python -m app.start  # runs migrations if enabled, then starts Uvicorn
```

Alternatively, run the server without the migration launcher:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Postgres (container)

See `postgres/README.md` for containerized deployment and DBeaver SSH-tunnel instructions. Attach API/Auth to the same Docker network and set `DATABASE_URL` accordingly.

## Notes

- This repo no longer includes a UI or Nginx-based static server.
- Reverse proxy and TLS are handled by Traefik on the host; services are private by default with optional public webhook exposure via labels.
