# Hostinger Deployment (Historical Reference)

⚠️ **NOTICE: This directory contains historical files only.**

## Current Deployment Model

**Service deployment files are located in each service's folder:**
- `postgres/postgres.compose.yml` - PostgreSQL VPS deployment
- `auth/auth.compose.yml` - Auth Service VPS deployment
- `webui/webui.compose.yml` - WebUI VPS deployment

**This `deploy/` folder contains global Docker infrastructure only:**
- `deploy/traefik/` - Traefik reverse proxy configuration
- `deploy/local/` - Local testing orchestration

## Historical Files (Preserved for Reference)

- `original-n8n/` - Original n8n setup before microservices refactoring
- `pasteables.md` - Historical deployment snippets

**Do not use these files for current deployments.**

---

## Deployment Instructions

### For VPS Deployment:
1. Go to service folder (e.g., `auth/`, `webui/`, `postgres/`)
2. Use `<service>.compose.yml` file
3. Deploy via Hostinger Docker UI (paste compose + set env vars)

### For Local Testing:
1. Go to `deploy/local/`
2. Use `docker-compose.local.yml` to orchestrate all services
3. Configure variables in `.env.local`
