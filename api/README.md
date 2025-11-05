# API deployment (private by default, optional public webhook)

This folder contains everything needed to build the API image in GitHub Actions and deploy it on Hostinger, attached to your existing Traefik network. By default the API is private (not reachable from the internet); n8n (and other services on the same Docker network) can call it internally as `http://api:8000`. You can optionally expose a narrow public webhook route via Traefik when needed.

## Image

- Name: `ghcr.io/jmnaste/ai-workflow-automation/api:main`
- Built by: `/.github/workflows/build-api.yml` on each push to `main`

## Deploy on Hostinger (private API)

1) In Hostinger → Docker → Compose → Create Project
2) Paste YAML from `api/api.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
TRAEFIK_NETWORK=root_default
# Optional if using Postgres: DSN on the private Docker network
# For psycopg driver:
DATABASE_URL=postgresql://app_system:YOUR_PASSWORD@postgres:5432/app_db
```

4) Deploy. No ports are published and no Traefik router is created; the API runs privately.

## Outbound internet access (egress)

No additional configuration is required for the API to make outbound HTTP(S) calls to public services; Docker provides NATed egress by default. Ensure your VPS firewall allows outbound traffic and DNS resolution works in your environment.

Quick check from outside (through the API):

- `curl -s "http://api:8000/api/egress/health"` → returns `{"status":"ok","url":"https://example.com","code":200}` when outbound works
- To test a specific endpoint: `curl -s "http://api:8000/api/egress/health?url=https://httpbin.org/status/204"`

## Expose a public webhook (optional)

If you need the API to receive webhooks from external systems, you can enable a narrowly scoped Traefik router that only matches a specific host and path prefix. This keeps the service private by default and only exposes what you intend.

1) In Hostinger → Edit the API project → Environment, add:

```
# Enable public routing via Traefik
API_PUBLIC=true

# Router host and path you control (examples)
API_WEBHOOK_HOST=webhooks.example.com
API_WEBHOOK_PATH_PREFIX=/webhook

# Traefik entrypoints (typically websecure for HTTPS)
API_ENTRYPOINTS=websecure

# TLS certificate resolver configured in your Traefik instance
TRAEFIK_CERT_RESOLVER=letsencrypt
```

2) Redeploy the project. Traefik will route requests matching:

- Host: `API_WEBHOOK_HOST`
- Path prefix: `API_WEBHOOK_PATH_PREFIX`

to the API container’s port 8000. Example public URL: `https://webhooks.example.com/webhook/...`

Security tips:

- Use a secret and unpredictable path, e.g., `/webhook/<random-token>`.
- Consider validating an HMAC signature or token header from the webhook sender.
- Optionally add Traefik middlewares (rate limit, IP allowlist, basic auth). These can be added as extra `traefik.http.middlewares.*` labels and referenced by the router.

## How n8n calls the API

In an n8n HTTP Request node (with n8n attached to the same Traefik network), use:

- URL: `http://api:8000/api/health`

The hostname `api` works because the compose file sets a network alias `api` on the Traefik network.

## Verify internally (optional)

- From inside the n8n container shell: `curl -s http://api:8000/api/health`
- From a temporary debug container attached to the network: `docker run --rm -it --network root_default curlimages/curl:8.10.1 curl -s http://api:8000/api/health`

If you configured `DATABASE_URL`, you can also check DB connectivity:

- `curl -s http://api:8000/api/db/health`

## Troubleshooting

- API unreachable from n8n:
  - Ensure both services are on the same Docker network (value of `TRAEFIK_NETWORK`).
  - Confirm the alias `api` exists: `docker network inspect <network> | jq '.[0].Containers'`.
- Image not found:
  - Confirm `ghcr.io/jmnaste/ai-workflow-automation/api:main` exists under GitHub Packages for this repo.
  - If your registry or namespace differs, edit the `image:` in the compose file accordingly.
- Need a fixed version:
  - Replace `:main` with the commit SHA tag published by the workflow (e.g., `:sha-<short>`).

- Public webhook not reachable:
  - Confirm `API_PUBLIC=true` and `API_WEBHOOK_HOST` are set.
  - Verify your DNS record points `API_WEBHOOK_HOST` to your Traefik entrypoint IP.
  - Ensure the specified `TRAEFIK_CERT_RESOLVER` exists in your Traefik configuration, or remove that label to use a preconfigured TLS setup.

## CI/CD notes

- The workflow logs into GHCR using the repository’s `GITHUB_TOKEN` and publishes tags:
  - `:main`
  - Branch ref tag
  - `:sha-...`
- To trigger manually: GitHub → Actions → Build and publish API image → Run workflow.
