# Deploy folder guide

Use the files under `deploy/hostinger/` for copy‑paste into Hostinger Compose.

Primary pasteables
- `hostinger/pasteables.md` — n8n environment panel lines and Traefik labels to attach n8n to your existing Traefik network.

Existing files (reference)
- `hostinger/original-n8n/` — Your original n8n stack (`docker-compose.yml` and `.env`).
- `hostinger/pasteables.md` — Longer guidance (copy‑paste focused) for Hostinger.

Notes
- The Traefik resolver name in labels is `mytlschallenge` to match a TLS‑ALPN challenge setup. Keep it consistent with your Traefik service args.
