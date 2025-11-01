# Hostinger pasteables: Environment panel + YAML snippets

This file gives you copy‑paste blocks for Hostinger’s Compose UI. Use the Environment block in the right panel, and paste the YAML snippets into the left YAML editor as directed.

Notes
- Keep one definition per variable. Do not duplicate keys with different values.
- Lines must be KEY=VALUE with no quotes and no spaces around =.
- The UI/API snippet assumes you’ll run this as an add‑on project that can access the `../ui` and `../api` build contexts (as in this repo). If you’re only editing your existing n8n project, use the “n8n labels only” block.

---

## 1) Environment panel (right side) — copy these lines

Paste one per line. Adjust the two hostnames to your domain.

```
# n8n public URL
N8N_HOST=n8n.coachstudio.com
N8N_PROTOCOL=https
N8N_PORT=5678
WEBHOOK_URL=https://n8n.coachstudio.com/

# n8n behind Traefik (trust proxy + recommended)
N8N_TRUSTED_PROXIES=loopback,linklocal,uniquelocal,172.16.0.0/12,10.0.0.0/8,192.168.0.0/16
N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true
# If using SQLite DB
DB_SQLITE_POOL_SIZE=1
# Future-proof runners and git node security
N8N_RUNNERS_ENABLED=true
N8N_GIT_NODE_DISABLE_BARE_REPOS=true
N8N_BLOCK_ENV_ACCESS_IN_NODE=false

# UI + API same-origin host
PRIMARY_HOST=workflow.coachstudio.com
UI_HOST=workflow.coachstudio.com

# Traefik external Docker network name (must match your existing Traefik network)
TRAEFIK_NETWORK=root_default

# Optional (if your Traefik is configured to use this for ACME)
SSL_EMAIL=user@srv948121.hstgr.cloud

# Optional, only if referenced in your n8n service env
GENERIC_TIMEZONE=Europe/Berlin
```

If you still have older values like `DOMAIN_NAME` and `SUBDOMAIN`, you can remove them or leave them unused. They won’t affect the explicit host setup below.

---

## 2) n8n labels only — paste under the n8n service `labels:` list

Use this when you’re modifying your existing Hostinger "root" project that already runs Traefik + n8n. Replace the current n8n labels block with the lines below.

```
traefik.enable=true
traefik.http.routers.n8n.rule=Host(`n8n.coachstudio.com`)
traefik.http.routers.n8n.entrypoints=websecure
traefik.http.routers.n8n.tls=true
traefik.http.routers.n8n.tls.certresolver=mytlschallenge
traefik.http.services.n8n.loadbalancer.server.port=5678

# Optional security headers (add after the site is working cleanly):
# traefik.http.middlewares.n8n-security.headers.stsSeconds=31536000
# traefik.http.middlewares.n8n-security.headers.forceSTSHeader=true
# traefik.http.routers.n8n.middlewares=n8n-security@docker
```

Tips
- Remove or update any old `sslHost` / `sslForceHost` middleware that points to the previous host; if you keep it, set it to `n8n.coachstudio.com`.
- Make sure the n8n service is attached to the Traefik network. At the bottom of your compose, declare the external network like this:

```
networks:
  traefik:
    external: true
    name: ${TRAEFIK_NETWORK}
```

And in the n8n service:

```
services:
  n8n:
    networks:
      - traefik
```

---

## 3) UI + API add‑on snippet — paste as a separate Hostinger project YAML

Use this if you’re creating a second (add‑on) project in Hostinger for the UI + API. It will attach to your existing Traefik network and serve the API at `/api` under the same host as the UI.

```
version: "3.9"

networks:
  traefik:
    external: true
    name: ${TRAEFIK_NETWORK}

services:
  ui:
    build:
      context: ../ui
    labels:
      - traefik.enable=true
      - traefik.http.routers.ui.rule=Host(`${UI_HOST}`) || Host(`${PRIMARY_HOST}`)
      - traefik.http.routers.ui.entrypoints=web,websecure
      - traefik.http.routers.ui.tls=true
      - traefik.http.routers.ui.tls.certresolver=mytlschallenge
    networks:
      - traefik
    restart: unless-stopped

  api:
    build:
      context: ../api
    labels:
      - traefik.enable=true
      # Same-origin path routing to avoid CORS
      - traefik.http.routers.api.rule=Host(`${PRIMARY_HOST}`) && PathPrefix(`/api`)
      - traefik.http.routers.api.entrypoints=web,websecure
      - traefik.http.routers.api.tls=true
      - traefik.http.routers.api.tls.certresolver=mytlschallenge
      - traefik.http.routers.api.priority=100
    networks:
      traefik:
        aliases:
          - api
    restart: unless-stopped
```

Requirements for this snippet
- The `../ui` and `../api` folders (with Dockerfiles) must exist relative to where Hostinger runs this compose. If they don’t, either deploy from the VPS using this repo’s layout or switch to prebuilt images.
- The `${TRAEFIK_NETWORK}` value must match the existing Traefik network name (e.g., `root_default`). Set it in the Environment panel.

---

## 4) Minimal verification (from Windows PowerShell)

```
# n8n hostname resolves
Resolve-DnsName n8n.coachstudio.com -Type A
Resolve-DnsName n8n.coachstudio.com -Type AAAA

# UI/API host resolves
Resolve-DnsName workflow.coachstudio.com -Type A
Resolve-DnsName workflow.coachstudio.com -Type AAAA

# After deploy, check redirects and TLS
curl.exe -I http://n8n.coachstudio.com
curl.exe -I https://n8n.coachstudio.com
curl.exe -vk https://n8n.coachstudio.com 2>&1 | Select-String -Pattern "subject:|issuer:|expire|start date"

# API health
curl.exe -sS https://workflow.coachstudio.com/api/health
```

If the browser still shows a warning after certificates are issued, try an incognito window or clear HSTS for the domain.
