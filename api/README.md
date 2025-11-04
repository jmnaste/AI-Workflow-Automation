# API deployment (Option A — private only)

This folder contains everything needed to build the API image in GitHub Actions and deploy it privately on Hostinger, attached to your existing Traefik network. The API won’t be reachable from the internet; n8n (and other services on the same Docker network) can call it internally as `http://api:8000`.

## Image

- Name: `ghcr.io/jmnaste/ai-workflow-automation/api:main`
- Built by: `/.github/workflows/build-api.yml` on each push to `main`

## Deploy on Hostinger (private API)

1) In Hostinger → Docker → Compose → Create Project
2) Paste YAML from `api/api.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
TRAEFIK_NETWORK=root_default
```

4) Deploy. No ports are published and no Traefik router is created; the API runs privately.

## How n8n calls the API

In an n8n HTTP Request node (with n8n attached to the same Traefik network), use:

- URL: `http://api:8000/api/health`

The hostname `api` works because the compose file sets a network alias `api` on the Traefik network.

## Verify internally (optional)

- From inside the n8n container shell: `curl -s http://api:8000/api/health`
- From a temporary debug container attached to the network: `docker run --rm -it --network root_default curlimages/curl:8.10.1 curl -s http://api:8000/api/health`

## Troubleshooting

- API unreachable from n8n:
  - Ensure both services are on the same Docker network (value of `TRAEFIK_NETWORK`).
  - Confirm the alias `api` exists: `docker network inspect <network> | jq '.[0].Containers'`.
- Image not found:
  - Confirm `ghcr.io/jmnaste/ai-workflow-automation/api:main` exists under GitHub Packages for this repo.
  - If your registry or namespace differs, edit the `image:` in the compose file accordingly.
- Need a fixed version:
  - Replace `:main` with the commit SHA tag published by the workflow (e.g., `:sha-<short>`).

## CI/CD notes

- The workflow logs into GHCR using the repository’s `GITHUB_TOKEN` and publishes tags:
  - `:main`
  - Branch ref tag
  - `:sha-...`
- To trigger manually: GitHub → Actions → Build and publish API image → Run workflow.
