# Auth service (private by default, optional public webhook)

A minimal FastAPI-based auth service, mirroring the API project structure. It runs privately on your Traefik Docker network and can optionally expose a narrow public webhook route via Traefik.

## Image

- Name: `ghcr.io/jmnaste/ai-workflow-automation/auth:main`
- Built by: `/.github/workflows/build-auth.yml` on each push to `main` or changes under `auth/`

## Deploy on Hostinger (private service)

1) In Hostinger → Docker → Compose → Create Project
2) Paste YAML from `auth/auth.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
TRAEFIK_NETWORK=root_default
# Optional if using Postgres: DSN on the private Docker network
DATABASE_URL=postgresql://app_system:YOUR_PASSWORD@postgres:5432/app_db
```

4) Deploy. No ports are published and no Traefik router is created; the service runs privately.

## Outbound internet access (egress)

No additional configuration is required for outbound HTTP(S); Docker provides NATed egress by default. Ensure your VPS allows outbound traffic and DNS resolution is working.

Quick checks from inside the network:

- `curl -s http://auth:8000/auth/health`
- `curl -s http://auth:8000/auth/egress/health`
- DB (if configured): `curl -s http://auth:8000/auth/db/health`

## Expose a public webhook (optional)

To receive webhooks from external systems, enable a narrowly scoped Traefik router:

In Hostinger → Edit the project → Environment, add:

```
AUTH_PUBLIC=true
AUTH_WEBHOOK_HOST=webhooks.example.com
AUTH_WEBHOOK_PATH_PREFIX=/webhook
AUTH_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt
```

Redeploy. Traefik will route only requests that match the configured host and path prefix to the auth service on port 8000.

Security tips:
- Use a secret/unpredictable path (e.g., `/webhook/<random-token>`)
- Validate signatures or tokens from the sender
- Optionally add Traefik middlewares (rate limit, IP allowlist, basic auth)

## Troubleshooting

- Service unreachable internally:
  - Confirm both services share the Traefik network (`TRAEFIK_NETWORK`).
  - Verify alias `auth` exists on the network.
- Image not found:
  - Confirm `ghcr.io/jmnaste/ai-workflow-automation/auth:main` exists under GitHub Packages.
- Need a fixed version:
  - Replace `:main` with a commit SHA tag published by the workflow (e.g., `:sha-<short>`).
