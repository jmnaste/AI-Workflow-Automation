# Development

This repository now ships only the API. There is no UI or Nginx-based static server.

## API (FastAPI)

- Python 3.12, FastAPI, Uvicorn
- Entrypoint: `app.main:app`
- Default port: `8000`
- Health: `GET /api/health` → `{ "status": "ok" }`

### Run locally

```bash
pip install -r api/requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Optional: If you test behind a reverse proxy (Traefik), configure it separately; this repo does not include proxy configs.
