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
# Database (required)
DATABASE_URL=postgresql://flovify:YOUR_PASSWORD@postgres:5432/flovify
# JWT (required - generate with: openssl rand -base64 32)
JWT_SECRET=your-secure-secret-at-least-32-chars
# OTP Configuration (optional - defaults shown)
OTP_EXPIRY_MINUTES=5
OTP_MAX_ATTEMPTS=3
RATE_LIMIT_WINDOW_MINUTES=15
RATE_LIMIT_MAX_REQUESTS=3
# Twilio SMS (optional - required if users choose SMS)
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=+1234567890
# SMTP Email (optional - required if users choose email)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@domain.com
SMTP_PASS=your-app-password
SMTP_FROM=noreply@flovify.ca
```

**Note**: Either Twilio OR SMTP must be configured for OTP delivery. Users choose their preferred method during sign-in.

4) Deploy. No ports are published and no Traefik router is created; the service runs privately.

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `TRAEFIK_NETWORK` | Traefik Docker network name | `root_default` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@postgres:5432/dbname` |
| `JWT_SECRET` | Secret for JWT signing (min 32 chars) | Generate with `openssl rand -base64 32` |

### OTP Configuration (Optional - defaults provided)

| Variable | Default | Description |
|----------|---------|-------------|
| `OTP_EXPIRY_MINUTES` | `5` | OTP code expiration time |
| `OTP_MAX_ATTEMPTS` | `3` | Max validation attempts per OTP |
| `RATE_LIMIT_WINDOW_MINUTES` | `15` | Rate limiting time window |
| `RATE_LIMIT_MAX_REQUESTS` | `3` | Max OTP requests per window |

### Delivery Methods (At least one required)

**Twilio SMS:**
| Variable | Description |
|----------|-------------|
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_PHONE_NUMBER` | Phone number with country code |

**SMTP Email:**
| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | - | SMTP server hostname |
| `SMTP_PORT` | `587` | SMTP port (587=TLS, 465=SSL) |
| `SMTP_USER` | - | SMTP username |
| `SMTP_PASS` | - | SMTP password |
| `SMTP_FROM` | `noreply@flovify.ca` | From email address |

**See [AUTH_CONFIGURATION.md](./AUTH_CONFIGURATION.md) for detailed configuration examples.**

### Configure the database DSN (DATABASE_URL)

Set the `DATABASE_URL` in the Hostinger Environment panel for this project. The compose file references it as `${DATABASE_URL}`.

Common formats (psycopg):

- Same Docker network (your own Postgres container):
  - `postgresql://app_system:YOUR_PASSWORD@postgres:5432/app_db`
  - Replace `postgres` with your Postgres service/alias name on the shared network.
  - Optional params: `?connect_timeout=3&application_name=auth`

- Managed/external Postgres (public hostname):
  - `postgresql://USER:PASS@HOST:PORT/DBNAME?sslmode=require&connect_timeout=3&application_name=auth`

Notes:
- URL‑encode special characters in passwords (e.g., `!` → `%21`).
- Prefer private networking between containers; require TLS (`sslmode=require`) across public networks.
- Verify with: `curl -s http://auth:8000/auth/db/health`

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

## Creating admin users

To create an admin user, use the `/auth/admin/create-user` endpoint with the `ADMIN_TOKEN`:

```bash
# See AUTH_CONFIGURATION.md for detailed curl examples (Windows CMD and Linux/Mac)
curl -X POST http://auth:8000/auth/admin/create-user \
  -H "X-Admin-Token: your_admin_token_here" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","phone":"+15551234567","preference":"sms","role":"admin"}'
```

**For complete API documentation and examples, see [AUTH_CONFIGURATION.md](./AUTH_CONFIGURATION.md).**

---

## Database migrations (manual SQL only)

This service owns the `auth` schema; migrations are applied manually via the numbered SQL files in `auth/migrations/`.

Key points:
- No automatic migration step runs at startup.
- Each migration file is idempotent where practical and records itself in `auth.migration_history`.
- Semantic version + timestamp pointer: `auth.schema_registry` (single row for `service='auth'`).
- History: `auth.schema_registry_history` maintains append-only records for audit.
- Health / diagnostics: `9999_health_check.sql` can be run safely at any time; it does not mutate versions.

Optional environment variable:
- `SERVICE_SEMVER`: If set when applying a migration, the footer can upsert that semver into `auth.schema_registry`. If not set, migrations fall back to a default embedded value.

Apply example inside the auth container (interactive):

```bash
docker exec -it <auth_container_name> psql -h postgres -U app_root -d app_db
\i /auth/migrations/0000_init_migration_history.sql
\i /auth/migrations/0001_auth_bootstrap.sql
\i /auth/migrations/0002_add_email_to_users.sql
\i /auth/migrations/0003_remove_alembic_artifacts.sql
```

Verification queries:

```sql
SELECT service, semver, ts_key, applied_at FROM auth.schema_registry;
SELECT service, semver, ts_key, applied_at FROM auth.schema_registry_history ORDER BY id DESC LIMIT 5;
SELECT schema_name, file_seq, name, applied_at FROM auth.migration_history ORDER BY file_seq;
```

### Inspect versions

- Recent applied versions (registry history): `GET /auth/versions?n=5`
- Service health: `GET /auth/health`

## Troubleshooting

- Service unreachable internally:
  - Confirm both services share the Traefik network (`TRAEFIK_NETWORK`).
  - Verify alias `auth` exists on the network.
- Image not found:
  - Confirm `ghcr.io/jmnaste/ai-workflow-automation/auth:main` exists under GitHub Packages.
- Need a fixed version:
  - Replace `:main` with a commit SHA tag published by the workflow (e.g., `:sha-<short>`).
