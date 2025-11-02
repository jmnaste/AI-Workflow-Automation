# UI development stack (React + TypeScript + Vite)

This document defines the recommended development setup for the UI. It prioritizes fast feedback (HMR), same‑origin API calls at `/api`, and a clean production path.

## Why this stack

- Vite dev server provides instant hot module reload.
- Same‑origin proxy to the API avoids CORS issues in dev and production.
- Production builds are static assets served by Nginx; no Node runtime required in prod.

## Summary

- Dev server: Vite (React + TypeScript) on http://localhost:5173
- API in dev: FastAPI on http://localhost:8001 (host) or `http://api:8000` when run in Docker
- Proxy: Vite proxies `/api` → API target, so the browser always calls `/api/...`
- Build: `vite build` → static `dist/` served by Nginx in the Docker image

## Prerequisites

- Node.js 20.x (use nvm-windows on Windows for easy switching)
- npm (or pnpm/yarn if you prefer)
- Python 3.12 for the API (or use Docker)

## Typical dev workflows

### 1) Run API on host, UI via Vite

- API (host):
  - Create and activate a venv, then:
  - `pip install -r api/requirements.txt`
  - `uvicorn app.main:app --reload --port 8001 --host 0.0.0.0`
- UI (Vite):
  - `cd ui`
  - `npm install`
  - `npm run dev`
  - Open http://localhost:5173

Vite will proxy `/api/*` to `http://localhost:8001` by default. If your API runs elsewhere, you can set `VITE_API_TARGET` in an `.env` file in `ui/`.

### 2) Run API in Docker, UI via Vite

- Start only the API service from the dev compose:
  - From repo root: `docker compose -f deploy/docker-compose.dev.yml up --build api`
- UI: same as above (`npm run dev`), but set the proxy target to Docker’s API endpoint.
  - In `ui/.env`: `VITE_API_TARGET=http://localhost:8000` if you publish the port, or `http://api:8000` if you develop with the UI in Docker as well.

## Project layout (UI)

- `ui/package.json` — scripts (`dev`, `build`, `preview`)
- `ui/vite.config.ts` — sets the `/api` proxy and React plugin
- `ui/tsconfig.json` — TypeScript config with JSX `react-jsx`
- `ui/index.html` — SPA entry
- `ui/src/main.tsx`, `ui/src/App.tsx` — minimal React app; calls `/api/health`

## Environment and proxy

- Default proxy target: `http://localhost:8001`
- Override with `.env` in `ui/`:
  - `VITE_API_TARGET=http://localhost:8001`

## Building for production

- Docker multi‑stage build:
  - Stage 1: Node builds the React app → `dist/`
  - Stage 2: Nginx serves `dist/` and proxies `/api/*` to `http://api:8000`
- CI builds the image and publishes it to GHCR; Hostinger pulls `:main` when you click Deploy.

## Optional extras

- Linting/formatting: ESLint + Prettier
- Testing: Vitest + React Testing Library
- Aliases: path aliases via `tsconfig` and `vite resolve.alias`

## Acceptance

- `npm run dev` gives HMR on http://localhost:5173
- `curl http://localhost:5173/api/health` returns `{ "status": "ok" }` when API is running
- `npm run build` produces a `dist/` suitable for the Nginx production image
