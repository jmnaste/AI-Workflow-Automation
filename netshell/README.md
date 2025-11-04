# NetShell project (separate private toolbox)

A small, persistent network shell container attached to your Traefik external Docker network so you can shell in and test connectivity to private services like the API via `http://api:8000`.

The default image is `wbitt/network-multitool:latest` (maintained successor of praqma/network-multitool), which includes curl, dig, nc, bash, etc. You can also build your own GHCR-hosted image from the provided Dockerfile.

## Manual deployment on Hostinger (first deploy)

1) Hostinger → Docker → Compose → Create Project (name it `netshell`)
2) Paste YAML from `netshell/netshell.compose.yml` into the left editor
3) Right panel → Environment (KEY=VALUE per line):

```
TRAEFIK_NETWORK=root_default
```

4) Deploy. The `net-debug` container will start and attach to the external network.

Open a shell:
- From Hostinger UI → Container → Console; or
- Via SSH: `docker exec -it net-debug sh`

Sanity check from inside the container:

```
curl -sS http://api:8000/api/health
```

## Manual — subsequent deploys/updates

- This project uses a public image tag. To refresh the container, just Redeploy the project in Hostinger (it pulls the latest tag if unchanged).
- No ports are exposed and Traefik is disabled; the container is private-only.

## GitHub-built image (optional)

If you prefer a reproducible, repository-owned image:

- The Dockerfile in `netshell/Dockerfile` builds a custom toolbox image based on `wbitt/network-multitool:latest`.
- The workflow `/.github/workflows/build-netshell.yml` builds and publishes to:
  - `ghcr.io/jmnaste/ai-workflow-automation/netshell:main`
  - plus branch/ref/sha tags

### First-time GHCR deploy

1) Trigger the GitHub Action: Actions → Build and publish NetShell image → Run workflow (or push to `main` with changes under `netshell/`).
2) Confirm the package appears in GitHub Packages (ensure visibility as needed).
3) In the Hostinger "netshell" project, edit `netshell/netshell.compose.yml` and change the image:

```
services:
  net-debug:
    image: ghcr.io/jmnaste/ai-workflow-automation/netshell:main
    command: ["sleep", "infinity"]
    labels:
      - traefik.enable=false
    networks:
      traefik: {}
    restart: unless-stopped
```

4) Redeploy. If the GHCR package is private, configure registry access in Hostinger or make it public.

### Subsequent GHCR-based updates

- When the workflow pushes a new image (e.g., on commit to main), you can:
  - Keep `:main` and use Hostinger's Redeploy to pull the updated digest; or
  - Pin to a `:sha-...` tag for deterministic rollouts, updating the tag in compose each deploy.

## Notes

- Keep `traefik.enable=false` and do not publish any ports — this is a private toolbox.
- Ensure `TRAEFIK_NETWORK` matches the exact name of your existing Traefik Docker network so `api` resolves internally.
