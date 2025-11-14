# AI Workflow Automation — AI Agent Instructions

## Project Overview

AI Workflow Automation platform with microservices architecture on Docker, deployed via GitHub Actions → GHCR → Hostinger VPS. Implements "Vibe Coding + Quality Gates" methodology: fast iteration loops with mandatory validation checkpoints.

**System Context**: Flovify provides specialized AI-powered primitives (email/document processing) that complement n8n workflow orchestration. n8n handles high-level business logic routing, Flovify handles AI analysis and external system integration.

**Core Architecture**: Private-by-default microservices on shared Docker network (`root_default`), fronted by Traefik reverse proxy.

```
Browser → Traefik (TLS) → WebUI (Nginx + BFF) → Private network → Auth / API / Postgres
n8n Workflows → API Service (AI primitives, webhook processing)
```

## Service Boundaries & Data Ownership

**Critical principle**: Each service owns its database schema. BFF never accesses database directly.

| Service | Port | Schema | Responsibilities | Database Access |
|---------|------|--------|------------------|-----------------|
| **Auth** | 8000 | `auth.*` | OTP authentication, JWT issuance, user identity, **OAuth credentials**, token management | Direct to `auth` schema |
| **API** | 8000 | `api.*` | **Webhooks**, business logic, LangGraph workflows, metrics | Direct to `api` schema |
| **WebUI BFF** | 3001 | None | Thin proxy, JWT cookie management, **OAuth callback routing** | **No database access** |
| **Postgres** | 5432 | All schemas | Data persistence | N/A (is the database) |
| **NetShell** | - | None | Network debugging toolbox | None |

### Credentials Model

**Credential = OAuth app configuration for external provider**: A "credential" represents OAuth application settings (client_id, client_secret, scopes) for connecting to an external provider. One Flovify installation can have multiple credentials per provider for different use cases.

**Example**: Flovify instance might have:
- 2 MS365 credentials (production + testing, or different tenants)
- 3 Google Workspace credentials (different scopes or environments)
- Future: Salesforce, Slack, custom OAuth providers

**Key Features**:
- **tenant_id** (optional): Azure AD tenant ID for single-tenant apps
- **Multiple credentials per provider**: Removed unique constraint on (provider, client_id) - allows testing different configurations
- **Encrypted storage**: Client secrets encrypted at rest using Fernet
- **Provider-specific callbacks**: `/bff/auth/webhook/ms365`, `/bff/auth/webhook/googlews`

**System Context**: Flovify complements n8n workflow implementation
- n8n = High-level workflow orchestration
- Flovify = Specialized AI-powered email/document processing primitives
- Integration: n8n workflows call Flovify API endpoints

**OAuth flow**:
1. User creates credential in Admin UI → stored in `auth.credentials`
2. User clicks "Connect" → BFF generates OAuth authorization URL
3. User consents on provider → redirect to `/bff/auth/webhook/{provider}`
4. BFF forwards to Auth `/auth/oauth/callback` with code and state
5. Auth exchanges code for tokens → stores in `auth.credential_tokens`
6. Auth marks credential as `connected` → redirects user to success page

**Auth Service** handles:
- OTP generation/validation (SMS via Twilio, Email via SMTP)
- JWT signing and validation
- User management (admin endpoints with `X-Admin-Token`)
- **Credential management**: OAuth app configurations (`auth.credentials`)
- **OAuth token storage**: Encrypted tokens per credential (`auth.credential_tokens`)
- **Token refresh**: Automatic renewal of expired OAuth tokens
- **Token exchange**: Backend OAuth callback handler

**User Roles** (defined in Auth service):
- **user**: Standard user with basic access
- **super-user**: Elevated user with additional business workflow privileges (NO admin console access)
- **admin**: Full administrative access including admin console and user management

**Critical**: Only `admin` role can access admin console (`/auth/admin/*`, `/bff/admin/*`). Super-user role has elevated business privileges but CANNOT access user management or admin endpoints.

**API Service** handles:
- **Webhook endpoints**: Receive MS365/Google notifications (`/api/ms365/webhook`, `/api/googlews/webhook`)
- **Subscription tracking**: Metadata for active webhooks (`api.webhook_subscriptions`)
- **Business process primitives**: Email parsing, document extraction, AI analysis
- **LangGraph workflows**: AI-powered processing and reasoning
- **n8n integration**: Exposes APIs for n8n workflow consumption
- **Token requests**: Requests OAuth tokens from Auth Service per tenant
- Business data (workflows, runs, agents)
- Startup gating: checks `auth.schema_registry.semver` against `API_MIN_AUTH_VERSION` env var

**BFF responsibilities**:
- Routes `/bff/auth/*` → Auth Service at `http://auth:8000`
- Routes `/bff/api/*` → API Service at `http://api:8000`
- **OAuth callback routing**: Provider-specific routes (`/bff/auth/webhook/ms365`, `/bff/auth/webhook/googlews`) forward to Auth
- Validates JWTs (extracts user info), sets httpOnly cookies
- **Does NOT** contain business logic or database queries

## Database Migration Strategy

**Manual SQL only — no Alembic/auto-migrations**. Each service owns its migration files:

- `auth/migrations/`: Auth schema migrations (0000, 0001, 0002, 0003, 9999)
- `api/migrations/`: API schema migrations (0000, 0001, 9999)
- `postgres/migrations/`: Bootstrap scripts (001_initial.sql)

**Applying migrations** (run from auth/api container using psql with `-h postgres`):
```bash
docker exec -it <auth_container> psql -h postgres -U app_root -d app_db -f /auth/migrations/0001_auth_bootstrap.sql
```

**Why `-h postgres`**: Service containers don't have local PostgreSQL sockets; must use TCP to `postgres` service DNS name.

**Migration conventions**:
- Zero-padded sequences: `0000_init_migration_history.sql` (MUST run first), `0001_`, `0002_`, etc.
- Idempotent: Use `IF NOT EXISTS`, `ON CONFLICT DO NOTHING`
- **GRANT statements**: Always included in migration files for `app_root` user (USAGE, CREATE, ALL PRIVILEGES on schema)
- Footer updates: `auth.migration_history`/`api.migration_history`, `auth.schema_registry`, `auth.schema_registry_history`
- Health checks: `9999_health_check.sql` (diagnostics only, doesn't mutate versions)

**Version registry** (`auth.schema_registry`):
- Single row per service: `(service, semver, ts_key, applied_at)`
- History table: `auth.schema_registry_history` (append-only audit)
- API gates startup on Auth version: `API_MIN_AUTH_VERSION=0.1.0`

## Development Workflow

**Semantic commits** (always use this format):
```
feat(scope): description     # New feature
fix(scope): description      # Bug fix
refactor(scope): description # Code restructuring
docs(scope): description     # Documentation
test(scope): description     # Tests
chore(scope): description    # Maintenance
```

**Commit workflow**: User says "I want to commit and update prompt log"

**Critical**: Copilot does NOT execute git commit. Copilot only:
1. **Updates prompt log** (`docs/Communication/prompt_log.md`):
   - Add entries for **creative, development-significant prompts only** from this commit cycle
   - Skip trivial clarifications, acknowledgments, or routine fixes
   - Format: `YYYY-MM-DD HH:MM` timestamp + full detailed prompt + synthesized 1-2 sentence outcome
2. **Checks last commit**: Run `git log -1` to see timestamp and message
3. **Analyzes changes**: Review files changed since last commit
4. **Proposes commit message**: Single semantic commit message (one phrase)
5. **Waits for approval**: Dev reviews and executes the actual `git commit` command

**Quality gates** (must pass before merge):
- Architecture Gate: Follows defined boundaries, no schema violations
- Code Gate: Linted, typed, tested
- Eval Gate: ≥90% golden tests passing
- Security Gate: No secrets in code, PII masked
- Documentation Gate: README/docs updated

**Vibe coding loop** (1-3 hour cycles):
1. Plan: Define intent and hypothesis
2. Build: Implement feature/node/flow
3. Evaluate: Run tests and evals
4. Document: Update docs automatically
5. Demo: Loom or dashboard screenshot

## Docker Compose & Deployment

**Image naming**: `ghcr.io/jmnaste/ai-workflow-automation/<service>:main`

Services built by GitHub Actions:
- `.github/workflows/build-auth.yml` → `auth:main`
- `.github/workflows/build-api.yml` → `api:main`
- `.github/workflows/build-webui.yml` → `webui:main`
- `.github/workflows/build-netshell.yml` → `netshell:main`

**Hostinger VPS deployment** (paste compose + env vars in Docker UI):
- Auth: `auth/auth.compose.yml` + env panel
- API: `api/api.compose.yml` + env panel
- WebUI: `webui/webui.compose.yml` + env panel
- Postgres: `postgres/postgres.compose.yml` + env panel
- NetShell: `netshell/netshell.compose.yml` + env panel

**Environment variables** (set in Hostinger UI, one KEY=VALUE per line):

**Auth Service** requires:
```bash
TRAEFIK_NETWORK=root_default
DATABASE_URL=postgresql://app_root:PASSWORD@postgres:5432/app_db
JWT_SECRET=<openssl rand -base64 32>
# OTP delivery (at least one):
TWILIO_ACCOUNT_SID=...  # For SMS
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1234567890
# OR:
SMTP_HOST=smtp.gmail.com  # For email
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
SMTP_FROM=noreply@flovify.ca
```

**WebUI (BFF)** requires:
```bash
TRAEFIK_NETWORK=root_default
UI_HOST=console.flovify.ca
UI_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt
NODE_ENV=production
API_BASE_URL=http://api:8000
AUTH_BASE_URL=http://auth:8000
JWT_SECRET=<same-as-auth-service>
JWT_COOKIE_NAME=flovify_token
```

**Optional public webhooks** (add to Auth or API service):
```bash
AUTH_PUBLIC=true
AUTH_WEBHOOK_HOST=webhooks.flovify.ca
AUTH_WEBHOOK_PATH_PREFIX=/webhook
AUTH_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt
```

**Local development**:
- Use `deploy/local/docker-compose.local.yml` for full stack
- Services use `.compose.local.yml` files with volume mounts for hot reload
- WebUI: `webui/local.compose.yml` → Vite dev server on `http://localhost:5173`

## Health & Diagnostics

**Always check health endpoints after changes:**

```bash
# Internal (from netshell or another container on network)
curl http://auth:8000/auth/health
curl http://auth:8000/auth/db/health
curl http://auth:8000/auth/egress/health
curl http://api:8000/api/health
curl http://api:8000/api/db/health
curl http://api:8000/api/egress/health

# External (via Traefik)
curl https://console.flovify.ca/ui/health
curl https://console.flovify.ca/bff/health
```

**Version inspection** (Auth service):
```bash
curl http://auth:8000/auth/versions?n=5
```

**Database verification** (exec into postgres or service container):
```sql
-- Check migration history
SELECT schema_name, file_seq, name, applied_at FROM auth.migration_history ORDER BY file_seq;
SELECT schema_name, file_seq, name, applied_at FROM api.migration_history ORDER BY file_seq;

-- Check version registry
SELECT service, semver, ts_key, applied_at FROM auth.schema_registry;
SELECT * FROM auth.schema_registry_history ORDER BY id DESC LIMIT 5;

-- List tables
\dt auth.*
\dt api.*
```

## Common Patterns

**FastAPI service structure**:
```python
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: run migrations, check dependencies."""
    run_migrations()
    check_auth_schema_version()  # API only
    yield

app = FastAPI(title="Service Name", version="0.1.0", lifespan=lifespan)

@app.get("/service/health")
def health():
    return {"status": "ok"}

@app.get("/service/db/health")
def db_health():
    # Test database connection
    pass
```

**JWT validation** (Auth service):
```python
import jwt as pyjwt
from fastapi import Header, HTTPException

def verify_jwt(authorization: str = Header(...)) -> dict:
    token = authorization.replace("Bearer ", "")
    try:
        return pyjwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except Exception:
        raise HTTPException(401, "Invalid token")
```

**Admin endpoints** (Auth service uses `X-Admin-Token` header):
```python
@app.post("/auth/admin/create-user")
def create_admin_user(x_admin_token: str = Header(...)):
    if x_admin_token != os.environ.get("ADMIN_TOKEN"):
        raise HTTPException(401, "Invalid admin token")
    # Create user logic
```

**BFF proxy pattern** (Node.js/Express):
```typescript
// Proxy to Auth Service
app.post('/bff/auth/request-otp', async (req, res) => {
  const response = await fetch('http://auth:8000/auth/request-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req.body)
  });
  const data = await response.json();
  res.json(data);
});

// Protected route: validate JWT from cookie
app.get('/bff/auth/me', verifyJwtMiddleware, async (req, res) => {
  // Forward to Auth with extracted user info
  const response = await fetch(`http://auth:8000/auth/me`, {
    headers: { 'Authorization': `Bearer ${req.jwt}` }
  });
  res.json(await response.json());
});
```

## Critical Gotchas

1. **BFF never queries database**: Route to Auth/API instead
2. **Migrations run manually**: No automatic startup migrations
3. **JWT_SECRET must match**: BFF and Auth must use same secret
4. **Docker DNS requires explicit host**: Use `-h postgres` in psql
5. **Private by default**: No Traefik routes unless `*_PUBLIC=true`
6. **Service-to-service**: Use internal DNS (`http://api:8000`, not `localhost`)
7. **Schema ownership**: Auth owns `auth.*`, API owns `api.*`
8. **Version gating**: API won't start if Auth schema version too old
9. **Semantic commits required**: Always use `type(scope): description` format
10. **Copilot doesn't commit**: When user says "commit + prompt log", Copilot updates log and proposes message but dev executes commit

## Tech Stack Reference

- **Backend**: Python 3.12, FastAPI, psycopg (not psycopg2)
- **Frontend**: React 18, TypeScript, Vite, Material UI v6
- **BFF**: Node.js 20, Express, TypeScript
- **Database**: PostgreSQL 16 (alpine), PGVector (future)
- **Auth**: JWT (pyjwt), OTP via Twilio SMS or SMTP email
- **Containers**: Docker, multi-stage builds
- **CI/CD**: GitHub Actions → GHCR
- **Reverse Proxy**: Traefik (Let's Encrypt TLS)
- **Deployment**: Hostinger VPS (Docker Compose UI)

## When to Use Each Service

**Modifying Auth Service** when:
- User identity, roles, permissions
- OTP/JWT authentication flows
- OAuth integrations (Microsoft 365, Google Workspace)
- Admin user management
- Schema changes to `auth.*` tables

**Modifying API Service** when:
- Business logic, workflows, agents
- LangGraph execution, RAG, AI orchestration
- Metrics, KPIs, observability data
- Schema changes to `api.*` tables

**Modifying WebUI/BFF** when:
- UI components, pages, routing
- BFF proxy routes or cookie handling
- Frontend state management, forms
- **Never** for database queries or business logic

**Database migrations** when:
- Adding/modifying tables, columns, indexes
- Backfilling data
- Performance optimizations (indexes, partitions)

**Infrastructure/deploy** when:
- Docker compose configs
- Environment variables
- Traefik routing rules
- CI/CD workflows

## KPIs & Reporting (Business-First)

**Client-facing dashboards** prioritize:
- Time-to-feature (time to benefit)
- Effectiveness trend (throughput, first-pass success)
- Before → After effectiveness index
- Error rate reduction, turnaround time improvement
- AI contribution stability & reliability

**Internal telemetry** (engineering diagnostics):
- p95/p99 latency, token/compute usage per run
- Retry counts, error codes
- Eval pass rates, golden set coverage

**Workflow run management UI** shows:
- Run list, run detail with state graph
- Retries, failure reasons, annotations
- Human-in-the-loop (HITL) decisions

## File Organization

```
/
├── .github/workflows/       # CI/CD (build-*.yml)
├── api/                     # API service (FastAPI)
│   ├── app/main.py          # Entrypoint
│   ├── migrations/          # Manual SQL for api schema
│   ├── Dockerfile           # Multi-stage build
│   └── api.compose.yml      # VPS deployment
├── auth/                    # Auth service (FastAPI)
│   ├── app/main.py          # Entrypoint
│   ├── migrations/          # Manual SQL for auth schema
│   ├── Dockerfile
│   └── auth.compose.yml
├── webui/                   # Frontend + BFF
│   ├── src/                 # React app
│   ├── bff/src/             # Express BFF
│   ├── nginx.conf           # Nginx config
│   ├── Dockerfile           # Multi-stage (React + BFF)
│   └── webui.compose.yml
├── postgres/                # Database container
│   ├── migrations/          # Bootstrap SQL
│   └── postgres.compose.yml
├── netshell/                # Network debugging
├── deploy/                  # Global infrastructure
│   ├── local/               # Local dev stack
│   ├── traefik/             # Traefik config
│   └── hostinger/           # VPS pasteables
└── docs/                    # Strategy, specs, prompts
    ├── Communication/prompt_log.md
    └── Inception/           # Vision docs
```

## Quick Reference Commands

**Run migrations**:
```bash
docker exec -it auth psql -h postgres -U app_root -d app_db -f /auth/migrations/0001_auth_bootstrap.sql
```

**Check logs**:
```bash
docker logs auth
docker logs api
docker logs webui
```

**Network debugging** (exec into netshell):
```bash
docker exec -it netshell sh
curl http://auth:8000/auth/health
curl http://api:8000/api/health
```

**Create admin user**:
```bash
curl -X POST http://auth:8000/auth/admin/create-user \
  -H "X-Admin-Token: your_token" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","phone":"+15551234567","preference":"sms","role":"admin"}'
```

**Generate JWT secret**:
```bash
openssl rand -base64 32
```

## When Something Breaks

1. **Check service health endpoints** (see Health & Diagnostics section)
2. **Verify Docker network**: `docker network inspect root_default`
3. **Check environment variables**: Hostinger UI → project → Environment tab
4. **Tail logs**: `docker logs <service> --tail 50 -f`
5. **Verify migrations applied**: Query `auth.migration_history`, `api.migration_history`
6. **Test service-to-service**: Exec into netshell, curl internal endpoints
7. **Check Traefik routes**: `docker logs traefik | grep <service>`
8. **Version mismatch**: API won't start if `API_MIN_AUTH_VERSION` > `auth.schema_registry.semver`

## Documentation Standards

- Keep README.md files up-to-date in each service folder
- Document environment variables with examples
- Include curl examples for API endpoints
- Update `docs/Communication/prompt_log.md` for significant changes
- Architecture decisions go in `docs/Inception/` or service-specific `ARCHITECTURE.md`
- Deployment steps in service `README.md` files
- No "TODO" comments in production code — use `TODO.md` or GitHub Issues

---

**Remember**: This is a private-by-default, schema-per-service, manual-migration, semantic-commit, quality-gated, vibe-coded monorepo. Speed with discipline. Build in vibe, validate in gates.
