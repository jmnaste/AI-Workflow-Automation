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

**API Service** uses **Process + Adapters architecture** (Hexagonal):

**Process Layer** (`api/app/processes/`):
- Business workflow orchestration (quote processing, email classification, workspace management)
- Coordinates multiple adapters to achieve business goals
- Provides high-level APIs for n8n consumption
- Applies domain logic and business rules
- **Platform-agnostic**: Same process works with MS365, Google, or future providers
- **Pattern**: Uses Dependency Injection (DI) with duck typing

**Adapters Layer** (`api/app/adapters/`):
- **Organization**: `adapters/{provider}/{service}.py` (e.g., `ms365/mail.py`, `googlews/mail.py`)
- **Providers**: ms365, googlews, database, storage
- **Services per provider**: mail (email operations), drive (file operations), calendar (event operations)
- **Primitives**: Atomic operations like `get_message()`, `create_folder()`, `send_message()`
- **Key principle**: Same interface across providers (normalized output)
- Abstracts external system integrations
- Handles auth, retries, rate limiting, error normalization

**Routes**:
- `/api/processes/*`: Process-level endpoints for n8n (business workflows)
- `/api/ms365/*`, `/api/googlews/*`: Adapter-level endpoints (webhooks, subscriptions)

**Documentation**:
- Full architecture: `docs/Architecture/architecture_decision.md`
- Refactor plan: `docs/Implementation/refactor_plan.md` (5 phases, 13-18 hours)
- Platform-agnostic patterns: `docs/Architecture/platform_agnostic_processes.md`
- Quick reference: `docs/Architecture/README.md`

### Architecture Deep Dive

**Process + Adapters Philosophy**:
- **Process Layer** = "What to do" (business intent in domain language)
- **Adapters Layer** = "How to do it" (technical implementation details)

**Example: Quote Request Workflow**
```python
# Process layer (processes/quote_processing.py)
async def handle_quote_request(event_id: str, mail_adapter, drive_adapter, storage_adapter):
    """Platform-agnostic: works with MS365 or Google"""
    # 1. Fetch email
    message = await mail_adapter.get_message(credential_id, message_id)
    
    # 2. Extract data (same format from any provider!)
    subject = message["subject"]
    from_email = message["from"]["address"]
    attachments = message["attachments"]  # Normalized!
    
    # 3. Create workspace folder
    folder_path = f"Quote_{from_email}_{date}"
    await storage_adapter.create_folder(folder_path)
    
    # 4. Save files
    await storage_adapter.write_json(f"{folder_path}/message.json", message)
    for attachment in attachments:
        await storage_adapter.save_file(f"{folder_path}/attachments/{attachment['name']}", attachment['content'])

# Adapter layer (adapters/ms365/mail.py)
async def get_message(credential_id: str, message_id: str) -> dict:
    """MS365-specific implementation"""
    graph_client = get_graph_client(credential_id)
    msg = await graph_client.me.messages.by_message_id(message_id).get()
    
    # Normalize to standard format
    return {
        "id": msg.id,
        "subject": msg.subject,
        "from": {"address": msg.from_.email_address.address, "name": msg.from_.email_address.name},
        "body": msg.body.content,
        "attachments": [normalize_attachment(a) for a in msg.attachments]
    }

# Adapter layer (adapters/googlews/mail.py)
async def get_message(credential_id: str, message_id: str) -> dict:
    """Google-specific implementation - SAME interface!"""
    gmail_service = get_gmail_client(credential_id)
    msg = gmail_service.users().messages().get(userId='me', id=message_id).execute()
    
    # Normalize to SAME format as MS365!
    return {
        "id": msg["id"],
        "subject": get_header(msg, "Subject"),
        "from": {"address": extract_email(msg), "name": extract_name(msg)},
        "body": extract_body(msg),
        "attachments": [normalize_attachment(a) for a in extract_attachments(msg)]
    }
```

**Key Benefits**:
1. **Platform-agnostic**: Change `mail_adapter=ms365.mail` to `mail_adapter=googlews.mail` and process still works
2. **Testable**: Mock adapters in unit tests, test process logic independently
3. **Maintainable**: Business logic separate from API integration details
4. **Extensible**: Add Salesforce adapter without touching process layer
5. **n8n-friendly**: High-level `/api/processes/*` endpoints hide complexity

**Python Pattern: Duck Typing + Dependency Injection**
- No formal interfaces required (Pythonic!)
- Process functions accept adapter parameters
- Runtime provider selection based on credential
- Optional `Protocol` type hints for IDE support

**Additional Responsibilities**:
- **Webhook receivers**: Store notifications in `api.webhook_events`
- **Background worker**: Processes pending webhook events, normalizes data
- **Token vending client**: Requests OAuth tokens from Auth Service
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

## Implementation Patterns from Codebase

**Current codebase patterns** (to be refactored into Process + Adapters):

**Custom Token Credential for MS365** (`ms365_service.py`):
```python
class FlovifyTokenCredential(TokenCredential):
    """
    Bridges msgraph-sdk authentication with Auth service token vending.
    Azure's TokenCredential requires sync get_token(), so uses httpx.Client.
    """
    def __init__(self, credential_id: str):
        self.credential_id = credential_id
    
    def get_token(self, *scopes: str, **kwargs) -> AccessToken:
        """Synchronous token fetch for msgraph-sdk compatibility"""
        url = f"{AUTH_SERVICE_URL}/auth/oauth/internal/credential-token"
        headers = {"X-Service-Token": SERVICE_SECRET}
        data = {"credential_id": self.credential_id}
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(url, headers=headers, json=data)
            response.raise_for_status()
            token_data = response.json()
        
        return AccessToken(
            token=token_data["access_token"],
            expires_on=token_data["expires_at"]
        )
```

**Error handling pattern** (custom exceptions):
```python
class MS365ServiceError(Exception):
    """Base exception for MS365 service errors"""
    pass

class AuthClientError(Exception):
    """Base exception for auth client errors"""
    pass

# Usage in functions
async def fetch_message(credential_id: str, message_id: str) -> dict:
    try:
        graph_client = get_graph_client(credential_id)
        message = await graph_client.me.messages.by_message_id(message_id).get()
        return normalize_message(message)
    except Exception as e:
        raise MS365ServiceError(f"Failed to fetch message: {e}")
```

**Webhook worker pattern** (background processing with retry):
```python
async def process_pending_events(batch_size: int = 10) -> Dict[str, int]:
    """
    Process webhook events with retry logic:
    1. SELECT FOR UPDATE SKIP LOCKED (concurrent worker safety)
    2. Mark as 'processing'
    3. Fetch full resource data
    4. Normalize payload
    5. Update status to 'completed' or increment retry_count
    """
    stats = {"processed": 0, "failed": 0, "skipped": 0}
    
    # Fetch pending events
    cur.execute("""
        SELECT id, credential_id, provider, external_resource_id, retry_count
        FROM api.webhook_events
        WHERE status = 'pending' AND retry_count < %s
        ORDER BY received_at ASC
        LIMIT %s
        FOR UPDATE SKIP LOCKED
    """, (MAX_RETRY_ATTEMPTS, batch_size))
    
    for event in events:
        try:
            # Mark processing
            cur.execute("UPDATE api.webhook_events SET status = 'processing' WHERE id = %s", (event_id,))
            
            # Fetch full data
            normalized = await process_ms365_event(...)
            
            # Mark completed
            cur.execute("""
                UPDATE api.webhook_events 
                SET status = 'completed', normalized_payload = %s 
                WHERE id = %s
            """, (json.dumps(normalized), event_id))
            
            stats["processed"] += 1
        except Exception as e:
            # Increment retry or mark failed
            cur.execute("""
                UPDATE api.webhook_events 
                SET status = CASE WHEN retry_count + 1 >= %s THEN 'failed' ELSE 'pending' END,
                    retry_count = retry_count + 1,
                    error_message = %s
                WHERE id = %s
            """, (MAX_RETRY_ATTEMPTS, str(e), event_id))
            stats["failed"] += 1
    
    return stats
```

**FastAPI Pydantic models** (request/response validation):
```python
class CreateSubscriptionRequest(BaseModel):
    credential_id: str = Field(..., description="UUID of the credential")
    resource: str = Field(..., examples=["me/mailFolders('inbox')/messages"])
    change_types: List[str] = Field(..., examples=[["created"]])
    notification_url: str = Field(..., examples=["https://webhooks.flovify.ca/..."])
    expiration_hours: int = Field(default=72, ge=1, le=4230)

class SubscriptionResponse(BaseModel):
    id: str
    credential_id: str
    provider: str
    status: str
    expires_at: Optional[datetime]
    created_at: datetime

@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=201)
async def create_webhook_subscription(request: CreateSubscriptionRequest):
    """Type-safe endpoint with validated request/response"""
    pass
```

**Environment configuration pattern**:
```python
# Worker configuration
WORKER_INTERVAL_SECONDS = int(os.getenv("WEBHOOK_WORKER_INTERVAL", "10"))
WORKER_BATCH_SIZE = int(os.getenv("WEBHOOK_WORKER_BATCH_SIZE", "10"))
MAX_RETRY_ATTEMPTS = int(os.getenv("WEBHOOK_MAX_RETRIES", "3"))

# Service-to-service auth
SERVICE_SECRET = os.getenv("SERVICE_SECRET")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth:8000")
```

**Worker lifecycle pattern** (FastAPI lifespan):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown hooks"""
    # Startup
    worker_task = asyncio.create_task(run_worker())
    yield
    # Shutdown
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="API Service", version="0.1.1", lifespan=lifespan)
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

## Layered Architecture: Process + Adapters

API Service follows **Hexagonal Architecture** with clear separation between business and technical concerns:

### **Process Layer** (`api/app/processes/`)
- **Purpose**: Business workflow orchestration
- **Responsibilities**: Quote processing, email classification, workspace management, document analysis
- **Dependencies**: Uses adapters, no direct external library dependencies
- **Naming**: `{capability}.py` → Functions: `handle_*()`, `process_*()`, `analyze_*()`
- **Example**: `quote_processing.py` orchestrates email analysis, attachment extraction, workspace creation

### **Adapters Layer** (`api/app/adapters/`)
- **Purpose**: External system integrations
- **Responsibilities**: Wrap MS365, Google, database, storage with clean interfaces
- **Dependencies**: Can use external libraries (msgraph-sdk, google-api, psycopg)
- **Naming**: `{system}_adapter.py` → Functions: `get_*()`, `fetch_*()`, `create_*()`, `download_*()`
- **Example**: `ms365_adapter.py` wraps Microsoft Graph API, handles auth, retries, normalization

### **When to Use Which Layer**

**Modifying Process Layer** when:
- Adding/changing business workflows (new email type, document processing)
- Orchestrating multi-step operations
- Applying business rules or logic
- Creating n8n-consumable endpoints

**Modifying Adapters Layer** when:
- Integrating new external system (Salesforce, Slack)
- Changing technical implementation (switch from local to S3 storage)
- Handling authentication, rate limiting, retries for external APIs
- Normalizing data formats from external systems

**Key Principle**: Process layer says "what to do" (business), Adapters layer says "how to do it" (technical).

See `docs/Architecture/layered_architecture.md` for detailed examples and patterns.

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

## Layered Architecture: Process + Adapters

API Service follows **Hexagonal Architecture** with clear separation between business and technical concerns:

### **Process Layer** (`api/app/processes/`)
- **Purpose**: Business workflow orchestration
- **Responsibilities**: Quote processing, email classification, workspace management, document analysis
- **Dependencies**: Uses adapters, no direct external library dependencies
- **Naming**: `{capability}.py` → Functions: `handle_*()`, `process_*()`, `analyze_*()`
- **Example**: `quote_processing.py` orchestrates email analysis, attachment extraction, workspace creation

### **Adapters Layer** (`api/app/adapters/`)
- **Purpose**: External system integrations
- **Responsibilities**: Wrap MS365, Google, database, storage with clean interfaces
- **Dependencies**: Can use external libraries (msgraph-sdk, google-api, psycopg)
- **Naming**: `{system}_adapter.py` → Functions: `get_*()`, `fetch_*()`, `create_*()`, `download_*()`
- **Example**: `ms365_adapter.py` wraps Microsoft Graph API, handles auth, retries, normalization

### **When to Use Which Layer**

**Modifying Process Layer** when:
- Adding/changing business workflows (new email type, document processing)
- Orchestrating multi-step operations
- Applying business rules or logic
- Creating n8n-consumable endpoints

**Modifying Adapters Layer** when:
- Integrating new external system (Salesforce, Slack)
- Changing technical implementation (switch from local to S3 storage)
- Handling authentication, rate limiting, retries for external APIs
- Normalizing data formats from external systems

**Key Principle**: Process layer says "what to do" (business), Adapters layer says "how to do it" (technical).

See `docs/Architecture/layered_architecture.md` for detailed examples and patterns.

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

## Quick Reference Cards

### **Architecture Cheat Sheet**

```
Process Layer (Business)          Adapters Layer (Technical)
─────────────────────────         ────────────────────────────
processes/                        adapters/
├── email_classification.py       ├── ms365/
├── quote_processing.py           │   ├── mail.py
├── workspace_management.py       │   ├── drive.py
└── document_analysis.py          │   └── _auth.py
                                  ├── googlews/
"What to do"                      │   ├── mail.py
Platform-agnostic                 │   └── drive.py
Business language                 ├── database.py
Uses adapters                     └── storage.py
No external APIs
                                  "How to do it"
                                  Provider-specific
                                  Technical details
                                  Handles auth, retries
```

### **API Endpoints Cheat Sheet**

```
Process Endpoints (n8n)           Adapter Endpoints (Infrastructure)
────────────────────────          ──────────────────────────────────
POST /api/processes/email/analyze POST /api/ms365/subscriptions
POST /api/processes/quote/handle  POST /api/ms365/webhook
POST /api/processes/workspace/create GET  /api/ms365/subscriptions/{id}
GET  /api/processes/events/pending PATCH /api/ms365/subscriptions/{id}/renew

High-level business operations    Low-level webhook/subscription mgmt
```

### **Terminology Cheat Sheet**

| Term | Definition | Example |
|------|------------|---------|
| **Adapter** | External system integration | `ms365`, `googlews`, `database` |
| **Service** | Capability within adapter | `mail`, `drive`, `calendar` |
| **Primitive** | Atomic operation | `get_message()`, `create_folder()` |
| **Process** | Business workflow | `quote_processing`, `email_classification` |
| **Provider** | Third-party platform | Microsoft 365, Google Workspace |
| **Credential** | OAuth app configuration | Client ID, secret, scopes |
| **Token** | OAuth access token | Encrypted, refreshable, stored in Auth |

### **Testing Workflow Cheat Sheet**

```bash
# 1. Health checks
curl http://auth:8000/auth/health
curl http://api:8000/api/health

# 2. Database check
psql -h postgres -U app_root -d app_db -c "SELECT * FROM auth.schema_registry;"

# 3. Test credential connection
curl http://api:8000/api/test/auth-validate/CREDENTIAL_ID

# 4. Test message fetching
curl http://api:8000/api/test/ms365/messages/CREDENTIAL_ID?limit=3

# 5. Worker logs
docker logs api --tail 50 | grep -i "worker"

# 6. Webhook events
psql -h postgres -U app_root -d app_db -c "SELECT * FROM api.webhook_events ORDER BY received_at DESC LIMIT 5;"
```

### **Refactoring Roadmap**

| Phase | Task | Duration | Status |
|-------|------|----------|--------|
| 0 | Test current code | 30-60 min | ⏳ In Progress |
| 1 | Create adapter structure | 2-3 hours | 📝 Planned |
| 2 | Create process layer | 3-4 hours | 📝 Planned |
| 3 | Add process endpoints | 1-2 hours | 📝 Planned |
| 4 | Add MS365 primitives | 2-3 hours | 📝 Planned |
| 5 | Implement GoogleWS | 4-5 hours | 📝 Planned |

**Total**: 13-18 hours  
**Documentation**: `docs/Implementation/refactor_plan.md`

### **Common Tasks Quick Commands**

**Run migration**:
```bash
docker exec -it auth psql -h postgres -U app_root -d app_db -f /auth/migrations/0001_auth_bootstrap.sql
```

**Create admin user**:
```bash
curl -X POST http://auth:8000/auth/admin/create-user \
  -H "X-Admin-Token: your_token" \
  -d '{"email":"admin@example.com","role":"admin"}'
```

**Check logs**:
```bash
docker logs auth --tail 50 -f
docker logs api --tail 50 -f
```

**Network debugging**:
```bash
docker exec -it netshell sh
curl http://auth:8000/auth/health
```

**Generate secrets**:
```bash
openssl rand -base64 32  # JWT_SECRET
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # ENCRYPTION_KEY
```

---

**Remember**: This is a private-by-default, schema-per-service, manual-migration, semantic-commit, quality-gated, vibe-coded monorepo. Speed with discipline. Build in vibe, validate in gates.
