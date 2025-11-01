# Deploy folder guide

Use the files under `deploy/hostinger/` for copy‑paste into Hostinger Compose.

Primary pasteables
- `hostinger/ui-api.env.paste.txt` — Environment panel lines. Edit the hostnames and Traefik network name if needed.
- `hostinger/ui-api.compose.paste.yml` — YAML for a separate UI+API project attached to your existing Traefik network (builds from local ../ui and ../api).
- `hostinger/ui-api.compose.from-github.yml` — Same UI+API, but builds directly from GitHub so you don’t need sources on the VPS.

Existing files (reference)
- `docker-compose.yml` — Add‑on compose for UI+API using local builds; functionally equivalent to the pasteable YAML.
- `.env.addon.example` — Minimal example of variables used by the add‑on compose.
- `hostinger/pasteables.md` — Longer guidance and alternative snippets.

Notes
- The Traefik resolver name in labels is `mytlschallenge` to match a TLS‑ALPN challenge setup. Keep it consistent with your Traefik service args.
- API is private by default (served only under `https://${PRIMARY_HOST}/api`).
- If n8n needs to call the API internally, the API service exposes a network alias `api` on the Traefik network (reachable as `http://api:8000`).
