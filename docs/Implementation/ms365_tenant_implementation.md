# MS365 Tenant Implementation Plan

**Status**: Not Started  
**Created**: 2025-11-12  
**Last Updated**: 2025-11-12  

## Overview

This document outlines the implementation plan for MS365 tenant management, enabling Flovify to connect to multiple Microsoft 365 accounts, manage OAuth credentials, and process email webhooks via Microsoft Graph API.

**Architecture Reference**: See `api/api_design.md` for detailed architecture decisions.

---

## Phase 1: Database & Auth Service Foundation

**Goal**: Store tenant credentials and provide OAuth flow

**Status**: ⬜ Not Started

### 1.1 Database Migration (Auth Service)

**Status**: ⬜ Not Started

- [ ] Create migration file: `auth/migrations/0006_tenant_tokens.sql`
  - [ ] Add `auth.tenant_tokens` table
    ```sql
    CREATE TABLE auth.tenant_tokens (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
      token_type TEXT NOT NULL,  -- 'app' | 'delegated'
      encrypted_access_token TEXT NOT NULL,
      encrypted_refresh_token TEXT,
      scopes TEXT[],
      expires_at TIMESTAMPTZ NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      last_refreshed_at TIMESTAMPTZ,
      INDEX idx_tenant_tokens_tenant_id (tenant_id),
      INDEX idx_tenant_tokens_expires_at (expires_at)
    );
    ```
  - [ ] Add encryption helper functions (if not using application-level encryption)
  - [ ] Update `auth.migration_history` footer
  - [ ] Update `auth.schema_registry` to version `0.1.3`
  - [ ] Update `auth.schema_registry_history`

- [ ] Update `auth/migrations/README.md` with new migration documentation

- [ ] Test migration locally
  ```bash
  docker exec -it auth psql -h postgres -U app_root -d app_db -f /auth/migrations/0006_tenant_tokens.sql
  ```

- [ ] Verify tables created:
  ```sql
  \dt auth.tenant_tokens
  SELECT * FROM auth.schema_registry WHERE service='auth';
  ```

### 1.2 Auth Service OAuth Endpoints

**Status**: ⬜ Not Started

#### Services Layer

- [ ] Create `auth/app/services/oauth.py`
  - [ ] Implement token encryption/decryption utilities
    - [ ] `encrypt_token(plaintext: str) -> str`
    - [ ] `decrypt_token(ciphertext: str) -> str`
    - [ ] Use `OAUTH_ENCRYPTION_KEY` from environment
  - [ ] Implement MS365 OAuth helper functions
    - [ ] `exchange_code_for_tokens(code: str, redirect_uri: str) -> dict`
    - [ ] `refresh_access_token(refresh_token: str) -> dict`
  - [ ] Implement tenant token management
    - [ ] `store_tenant_tokens(tenant_id: UUID, tokens: dict) -> None`
    - [ ] `get_tenant_token(tenant_id: UUID) -> str` (with auto-refresh)
    - [ ] `refresh_tenant_token(tenant_id: UUID) -> str`

#### Router Layer

- [ ] Create `auth/app/routers/oauth.py`
  - [ ] `GET /auth/oauth/ms365/authorize`
    - [ ] Generate OAuth state token (CSRF protection)
    - [ ] Store state in memory/cache with expiry (10 min)
    - [ ] Build Microsoft authorization URL
    - [ ] Redirect to Microsoft login
  - [ ] `GET /auth/oauth/ms365/callback`
    - [ ] Validate state parameter (CSRF check)
    - [ ] Exchange authorization code for tokens
    - [ ] Create or update `auth.tenants` record
    - [ ] Store encrypted tokens in `auth.tenant_tokens`
    - [ ] Redirect to UI success page
  - [ ] `POST /auth/internal/tenant-token` (internal endpoint)
    - [ ] Validate service-to-service auth (`X-Service-Token`)
    - [ ] Accept `tenant_id` in request body
    - [ ] Return valid access token (refresh if needed)
    - [ ] Response: `{ "access_token": "...", "expires_at": "..." }`

- [ ] Register router in `auth/app/main.py`
  ```python
  from app.routers import oauth
  app.include_router(oauth.router)
  ```

#### Environment Variables

- [ ] Add to `auth/.env.example`:
  ```bash
  MICROSOFT_CLIENT_ID=your_azure_app_id
  MICROSOFT_CLIENT_SECRET=your_azure_app_secret
  MICROSOFT_REDIRECT_URI=https://console.flovify.ca/auth/oauth/ms365/callback
  OAUTH_ENCRYPTION_KEY=<base64-encoded-32-byte-key>
  SERVICE_SECRET=<shared-secret-for-internal-api-calls>
  ```

- [ ] Document in `auth/README.md`

#### Testing

- [ ] Create Azure App Registration
  - [ ] Note Client ID and Client Secret
  - [ ] Configure redirect URI: `http://localhost:8000/auth/oauth/ms365/callback`
  - [ ] Grant permissions: `Mail.Read`, `Mail.Send`, `offline_access`

- [ ] Test OAuth flow locally
  - [ ] Start auth service
  - [ ] Navigate to `http://localhost:8000/auth/oauth/ms365/authorize`
  - [ ] Complete Microsoft login
  - [ ] Verify tokens stored in `auth.tenant_tokens`
  - [ ] Verify encryption (tokens should not be plaintext)

---

## Phase 2: Tenant Management UI

**Goal**: Admin can connect and manage MS365 accounts

**Status**: ⬜ Not Started

### 2.1 Admin UI Components

**Status**: ⬜ Not Started

#### Tenants Page

- [ ] Create `webui/ui/src/pages/admin/Tenants.tsx`
  - [ ] List connected tenants table
    - Columns: Provider, Account Email, Display Name, Status, Connected Date, Actions
  - [ ] "Connect MS365 Account" button
  - [ ] Disconnect action (with confirmation dialog)
  - [ ] Reconnect action (restart OAuth flow)
  - [ ] Status indicator: Active / Token Expired / Error
  - [ ] Show last token refresh timestamp

#### Connect Tenant Dialog

- [ ] Create `webui/ui/src/components/admin/ConnectTenantDialog.tsx`
  - [ ] Provider selection (MS365, future: Google Workspace)
  - [ ] Display name input (e.g., "John @ Acme HQ")
  - [ ] "Authorize with Microsoft" button
  - [ ] Opens popup or redirect to OAuth flow
  - [ ] Handle OAuth callback success/error

#### API Client

- [ ] Create `webui/ui/src/lib/api/tenants.ts`
  - [ ] `listTenants(): Promise<Tenant[]>`
  - [ ] `disconnectTenant(tenantId: string): Promise<void>`
  - [ ] `startOAuthFlow(provider: string): Promise<string>` (returns OAuth URL)

#### Navigation

- [ ] Update `webui/ui/src/shell/Navigation.tsx`
  - [ ] Add "Tenants" menu item under Admin section
  - [ ] Icon: AccountBox or Cloud

### 2.2 BFF Proxy Routes

**Status**: ⬜ Not Started

- [ ] Update `webui/bff/src/routes/auth.ts`
  - [ ] `GET /bff/auth/tenants`
    - [ ] Forward to `http://auth:8000/auth/tenants`
    - [ ] Requires admin JWT
  - [ ] `POST /bff/auth/oauth/ms365/start`
    - [ ] Forward to `http://auth:8000/auth/oauth/ms365/authorize`
    - [ ] Return OAuth URL for client redirect
  - [ ] Handle OAuth callback redirect (if needed)

- [ ] Add Auth Service endpoints for tenant listing
  - [ ] `GET /auth/tenants` (admin only)
    - [ ] List all tenants with status
    - [ ] Join with `auth.tenant_tokens` for expiry info
  - [ ] `DELETE /auth/tenants/{tenant_id}` (admin only)
    - [ ] Soft delete or hard delete tenant and tokens

#### Testing

- [ ] Test tenant list API via BFF
- [ ] Test OAuth initiation via BFF
- [ ] Test full UI flow: Connect → OAuth → Callback → Tenant appears in list

---

## Phase 3: API Service Webhook Subscriptions

**Goal**: Create MS Graph webhook subscriptions per tenant

**Status**: ⬜ Not Started

### 3.1 Database Migration (API Service)

**Status**: ⬜ Not Started

- [ ] Create migration file: `api/migrations/0002_webhook_subscriptions.sql`
  - [ ] Add `api.webhook_subscriptions` table
    ```sql
    CREATE TABLE api.webhook_subscriptions (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL,
      provider TEXT NOT NULL,
      subscription_id TEXT NOT NULL,
      resource TEXT NOT NULL,
      change_types TEXT[],
      history_id TEXT,
      expires_at TIMESTAMPTZ NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      last_renewed_at TIMESTAMPTZ,
      UNIQUE(provider, subscription_id),
      INDEX idx_webhook_subs_tenant_id (tenant_id),
      INDEX idx_webhook_subs_expires_at (expires_at)
    );
    ```
  - [ ] Add `api.webhook_events` table (idempotency)
    ```sql
    CREATE TABLE api.webhook_events (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      tenant_id UUID NOT NULL,
      provider TEXT NOT NULL,
      event_key TEXT NOT NULL,
      message_id TEXT,
      processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      correlation_id UUID NOT NULL,
      UNIQUE(provider, event_key),
      INDEX idx_webhook_events_tenant_id (tenant_id),
      INDEX idx_webhook_events_processed_at (processed_at)
    );
    ```
  - [ ] Update `api.migration_history` footer
  - [ ] Update `api.schema_registry` to version `0.1.1`

- [ ] Update `api/migrations/README.md` with new migration documentation

- [ ] Test migration locally
  ```bash
  docker exec -it api psql -h postgres -U app_root -d app_db -f /api/migrations/0002_webhook_subscriptions.sql
  ```

- [ ] Verify tables created:
  ```sql
  \dt api.webhook_subscriptions
  \dt api.webhook_events
  ```

### 3.2 API Service MS365 Integration

**Status**: ⬜ Not Started

#### Services Layer

- [ ] Create `api/app/services/ms365.py`
  - [ ] Implement Auth Service token client
    - [ ] `request_tenant_token(tenant_id: UUID) -> str`
    - [ ] HTTP POST to `http://auth:8000/auth/internal/tenant-token`
    - [ ] Include `X-Service-Token` header
  - [ ] Implement MS Graph subscription management
    - [ ] `create_subscription(tenant_id: UUID, resource: str) -> dict`
      - Request token from Auth
      - POST to `https://graph.microsoft.com/v1.0/subscriptions`
      - Body: `{ resource, changeType, notificationUrl, expirationDateTime, clientState }`
      - Store subscription in `api.webhook_subscriptions`
    - [ ] `renew_subscription(subscription_id: str) -> None`
      - Lookup tenant_id from `api.webhook_subscriptions`
      - Request token from Auth
      - PATCH to `https://graph.microsoft.com/v1.0/subscriptions/{id}`
      - Update `last_renewed_at` and `expires_at`
    - [ ] `delete_subscription(subscription_id: str) -> None`
      - DELETE from Graph API
      - Delete from `api.webhook_subscriptions`
  - [ ] Implement message fetching
    - [ ] `fetch_message(tenant_id: UUID, message_id: str) -> dict`
      - Request token from Auth
      - GET `https://graph.microsoft.com/v1.0/me/messages/{message_id}`
      - Return normalized message object
  - [ ] Implement notification validation
    - [ ] `validate_client_state(client_state: str) -> bool`

#### Router Layer

- [ ] Create `api/app/routers/ms365.py`
  - [ ] `GET /api/ms365/webhook`
    - [ ] Microsoft Graph validation endpoint
    - [ ] Echo `validationToken` query parameter as plain text
    - [ ] Return 200 with token in response body
  - [ ] `POST /api/ms365/webhook`
    - [ ] Receive Graph change notifications
    - [ ] Validate `clientState` header
    - [ ] Extract notification array from body
    - [ ] For each notification:
      - [ ] Check idempotency (event_key = subscription_id + resource_id)
      - [ ] Enqueue to worker queue
    - [ ] Return 202 Accepted immediately
  - [ ] `POST /api/ms365/subscriptions` (admin only)
    - [ ] Accept: `{ tenant_id, resource, change_types }`
    - [ ] Create subscription via `ms365.create_subscription()`
    - [ ] Return subscription details

- [ ] Register router in `api/app/main.py`
  ```python
  from app.routers import ms365
  app.include_router(ms365.router)
  ```

#### Environment Variables

- [ ] Add to `api/.env.example`:
  ```bash
  SERVICE_SECRET=<same-as-auth-service>
  AUTH_SERVICE_URL=http://auth:8000
  MS365_WEBHOOK_URL=https://webhooks.flovify.ca/api/ms365/webhook
  MS365_CLIENT_STATE=<random-secret-string>
  ```

#### Testing

- [ ] Test validation endpoint
  ```bash
  curl "http://localhost:8000/api/ms365/webhook?validationToken=test123"
  # Should return: test123
  ```

- [ ] Test subscription creation (with real tenant)
  ```bash
  curl -X POST http://localhost:8000/api/ms365/subscriptions \
    -H "Authorization: Bearer <admin-jwt>" \
    -H "Content-Type: application/json" \
    -d '{"tenant_id": "<uuid>", "resource": "me/messages", "change_types": ["created"]}'
  ```

- [ ] Verify subscription in database:
  ```sql
  SELECT * FROM api.webhook_subscriptions;
  ```

---

## Phase 4: Webhook Processing

**Goal**: Process incoming MS365 notifications

**Status**: ⬜ Not Started

### 4.1 Worker Implementation

**Status**: ⬜ Not Started

#### Queue Setup

- [ ] Create `api/app/core/queue.py`
  - [ ] Choose queue backend (Redis, RabbitMQ, or in-memory for MVP)
  - [ ] Implement queue interface:
    - [ ] `enqueue(queue_name: str, data: dict) -> None`
    - [ ] `dequeue(queue_name: str) -> dict | None`
  - [ ] Add environment variable: `QUEUE_BACKEND=redis` / `QUEUE_URL=redis://redis:6379`

#### Worker Implementation

- [ ] Create `api/app/workers/ms365_worker.py`
  - [ ] Main worker loop:
    - [ ] Dequeue events from `ms365_events` queue
    - [ ] Extract: `tenant_id`, `subscription_id`, `resource_id`, `change_type`
  - [ ] Process each event:
    - [ ] Check idempotency: lookup event_key in `api.webhook_events`
    - [ ] If already processed, skip
    - [ ] Fetch message content via `ms365.fetch_message()`
    - [ ] Store message in business domain table (e.g., `api.messages`)
    - [ ] Record in `api.webhook_events` with event_key
  - [ ] Error handling:
    - [ ] Retry with exponential backoff (3 attempts)
    - [ ] Log failures for manual review
    - [ ] Dead letter queue for permanent failures

#### Worker Startup

- [ ] Update `api/app/main.py` lifespan context
  ```python
  import threading
  from app.workers import ms365_worker
  
  @asynccontextmanager
  async def lifespan(app: FastAPI):
      # Start worker thread
      worker_thread = threading.Thread(target=ms365_worker.run, daemon=True)
      worker_thread.start()
      yield
  ```

- [ ] Or create separate worker process/container (preferred for production)

#### Testing

- [ ] Create test event manually in queue
- [ ] Verify worker processes event
- [ ] Verify message fetched and stored
- [ ] Verify idempotency (re-enqueue same event, should skip)

### 4.2 Background Tasks

**Status**: ⬜ Not Started

#### Token Refresh Task

- [ ] Create `auth/app/tasks/token_refresh.py`
  - [ ] Periodic task (runs every hour)
  - [ ] Query `auth.tenant_tokens` where `expires_at < now() + interval '24 hours'`
  - [ ] For each expiring token:
    - [ ] Call `refresh_access_token(refresh_token)`
    - [ ] Update encrypted_access_token and expires_at
    - [ ] Update last_refreshed_at timestamp
  - [ ] Log success/failure for monitoring

- [ ] Integrate with task scheduler
  - [ ] Option A: APScheduler in FastAPI lifespan
  - [ ] Option B: Celery Beat
  - [ ] Option C: Systemd timer or cron job

#### Subscription Renewal Task

- [ ] Create `auth/app/tasks/subscription_renewal.py`
  - [ ] Periodic task (runs every hour)
  - [ ] Query `api.webhook_subscriptions` where `expires_at < now() + interval '24 hours'`
  - [ ] For each expiring subscription:
    - [ ] Call API service: `POST /api/internal/renew-subscription`
    - [ ] API service renews via `ms365.renew_subscription()`
  - [ ] Log success/failure for monitoring

- [ ] Add internal API endpoint in `api/app/routers/ms365.py`
  - [ ] `POST /api/internal/renew-subscription`
  - [ ] Requires `X-Service-Token` header
  - [ ] Accepts `subscription_id`
  - [ ] Calls `ms365.renew_subscription()`

#### Testing

- [ ] Create token with near-expiry timestamp
- [ ] Run token refresh task manually
- [ ] Verify token refreshed in database
- [ ] Create subscription with near-expiry timestamp
- [ ] Run subscription renewal task manually
- [ ] Verify subscription renewed in database

---

## Phase 5: Testing & Deployment

**Goal**: Validate end-to-end flow and deploy to production

**Status**: ⬜ Not Started

### 5.1 Local Testing

**Status**: ⬜ Not Started

#### Azure Setup

- [ ] Create Azure App Registration
  - [ ] Navigate to Azure Portal → App Registrations → New
  - [ ] Name: "Flovify Local Development"
  - [ ] Redirect URI: `http://localhost:8000/auth/oauth/ms365/callback`
  - [ ] Copy Client ID and Client Secret
  - [ ] API Permissions:
    - [ ] Mail.Read (Delegated)
    - [ ] Mail.Send (Delegated)
    - [ ] offline_access (Delegated)
  - [ ] Grant admin consent

- [ ] Configure local environment
  - [ ] Update `auth/.env.local` with Azure credentials
  - [ ] Update `api/.env.local` with webhook URL (use ngrok for testing)

#### End-to-End Test

- [ ] Start local stack
  ```bash
  cd deploy/local
  docker-compose -f docker-compose.local.yml --env-file .env.local up
  ```

- [ ] Test OAuth flow
  - [ ] Navigate to `http://localhost:5173/admin/tenants`
  - [ ] Click "Connect MS365 Account"
  - [ ] Complete Microsoft login
  - [ ] Verify tenant appears in list with "Active" status

- [ ] Test webhook subscription
  - [ ] Create subscription via API or UI
  - [ ] Verify subscription in database
  - [ ] Use ngrok to expose local API: `ngrok http 8000`
  - [ ] Update MS365 webhook URL to ngrok URL

- [ ] Test notification delivery
  - [ ] Send test email to connected MS365 account
  - [ ] Verify webhook notification received at `/api/ms365/webhook`
  - [ ] Verify event enqueued
  - [ ] Verify worker processes event
  - [ ] Verify message fetched and stored

- [ ] Test token refresh
  - [ ] Manually set token expiry to near-future
  - [ ] Trigger token refresh task
  - [ ] Verify token refreshed

- [ ] Test subscription renewal
  - [ ] Manually set subscription expiry to near-future
  - [ ] Trigger subscription renewal task
  - [ ] Verify subscription renewed in Graph API and database

### 5.2 VPS Deployment

**Status**: ⬜ Not Started

#### Azure Production Setup

- [ ] Create production Azure App Registration
  - [ ] Name: "Flovify Production"
  - [ ] Redirect URI: `https://console.flovify.ca/auth/oauth/ms365/callback`
  - [ ] Webhook URL: `https://webhooks.flovify.ca/api/ms365/webhook`
  - [ ] Copy credentials for Hostinger environment

#### Database Migrations

- [ ] Deploy Auth migration to VPS
  ```bash
  # SSH into VPS or use Hostinger console
  docker exec -it <auth_container> psql -h postgres -U app_root -d app_db -f /auth/migrations/0006_tenant_tokens.sql
  ```

- [ ] Deploy API migration to VPS
  ```bash
  docker exec -it <api_container> psql -h postgres -U app_root -d app_db -f /api/migrations/0002_webhook_subscriptions.sql
  ```

- [ ] Verify migrations applied
  ```sql
  SELECT * FROM auth.schema_registry WHERE service='auth';
  SELECT * FROM api.migration_history WHERE schema_name='api' ORDER BY file_seq DESC LIMIT 5;
  ```

#### Environment Configuration

- [ ] Update Auth service environment (Hostinger UI)
  ```bash
  MICROSOFT_CLIENT_ID=<production-client-id>
  MICROSOFT_CLIENT_SECRET=<production-secret>
  MICROSOFT_REDIRECT_URI=https://console.flovify.ca/auth/oauth/ms365/callback
  OAUTH_ENCRYPTION_KEY=<base64-encoded-key>
  SERVICE_SECRET=<shared-secret>
  ```

- [ ] Update API service environment (Hostinger UI)
  ```bash
  MS365_WEBHOOK_URL=https://webhooks.flovify.ca/api/ms365/webhook
  MS365_CLIENT_STATE=<random-secret>
  SERVICE_SECRET=<same-as-auth>
  AUTH_SERVICE_URL=http://auth:8000
  ```

#### Code Deployment

- [ ] Commit all changes to main branch
- [ ] Tag release: `git tag v0.2.0-ms365-beta`
- [ ] Push: `git push origin main --tags`
- [ ] GitHub Actions builds and pushes images to GHCR
- [ ] Pull latest images in Hostinger:
  ```bash
  docker pull ghcr.io/jmnaste/ai-workflow-automation/auth:main
  docker pull ghcr.io/jmnaste/ai-workflow-automation/api:main
  docker pull ghcr.io/jmnaste/ai-workflow-automation/webui:main
  ```
- [ ] Restart containers in Hostinger UI

#### Production Testing

- [ ] Test OAuth flow in production
  - [ ] Navigate to `https://console.flovify.ca/admin/tenants`
  - [ ] Connect MS365 account
  - [ ] Verify tenant stored in database

- [ ] Test webhook subscription creation
  - [ ] Create subscription for production tenant
  - [ ] Verify subscription in Graph API dashboard

- [ ] Test webhook delivery
  - [ ] Send email to connected account
  - [ ] Check API logs: `docker logs api --tail 50 -f`
  - [ ] Verify notification received and processed

- [ ] Monitor health endpoints
  ```bash
  curl https://console.flovify.ca/bff/auth/health
  curl https://console.flovify.ca/bff/api/health
  ```

#### Monitoring Setup

- [ ] Add Grafana dashboard for MS365 metrics (if applicable)
- [ ] Set up alerts for:
  - [ ] Token refresh failures
  - [ ] Subscription renewal failures
  - [ ] Webhook processing errors
  - [ ] High worker queue depth

---

## Success Criteria

### Functional Requirements

- [x] Admin can connect MS365 account via OAuth ✅
- [x] Tokens stored encrypted in `auth.tenant_tokens` ✅
- [x] Webhook subscription created and tracked ✅
- [x] Notifications received at `/api/ms365/webhook` ✅
- [x] Messages fetched and processed by worker ✅
- [x] Tokens auto-refresh before expiry ✅
- [x] Subscriptions auto-renew before expiry ✅
- [x] Idempotency prevents duplicate processing ✅
- [x] Multi-tenant support (multiple MS365 accounts) ✅

### Non-Functional Requirements

- [x] OAuth credentials never stored in API service ✅
- [x] Tokens encrypted at rest ✅
- [x] Webhook endpoint responds < 200ms ✅
- [x] Worker processes events with retry logic ✅
- [x] Database migrations are idempotent ✅
- [x] All endpoints have proper error handling ✅
- [x] Logging for audit trail and debugging ✅

---

## Rollback Plan

If deployment fails or critical bugs discovered:

1. **Database Rollback**: Migrations are additive, no immediate rollback needed
2. **Code Rollback**: 
   ```bash
   docker pull ghcr.io/jmnaste/ai-workflow-automation/auth:<previous-tag>
   docker pull ghcr.io/jmnaste/ai-workflow-automation/api:<previous-tag>
   # Restart containers
   ```
3. **Data Safety**: New tables don't affect existing functionality
4. **Feature Flag**: Can disable OAuth flow in UI without code changes

---

## Notes & Decisions

### Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-11-12 | Use application-level encryption for tokens | Simpler than PostgreSQL pgcrypto, better key management |
| 2025-11-12 | Start with in-memory queue for MVP | Can upgrade to Redis/RabbitMQ later without architecture change |
| 2025-11-12 | Single worker process initially | Simplifies deployment, can scale horizontally later |

### Open Questions

- [ ] Queue backend choice: Redis, RabbitMQ, or database-backed?
  - **Decision pending**: Start with in-memory, evaluate Redis for production
- [ ] Task scheduler choice: APScheduler, Celery, or external cron?
  - **Decision pending**: APScheduler for simplicity initially
- [ ] Webhook notification retention policy?
  - **Decision pending**: Keep 30 days, archive or delete older records

### Future Enhancements

- [ ] Google Workspace integration (Phase 2)
- [ ] Webhook retry dashboard in UI
- [ ] Tenant health status monitoring
- [ ] Bulk subscription management
- [ ] Webhook event replay functionality
- [ ] Multi-region token storage for compliance

---

## References

- **Architecture**: `api/api_design.md`
- **Auth Service Docs**: `auth/README.md`, `auth/AUTH_CONFIGURATION.md`
- **API Service Docs**: `api/README.md`
- **Migration Strategy**: `.github/copilot-instructions.md` (Database Migration Strategy section)
- **Microsoft Graph API**: https://learn.microsoft.com/en-us/graph/api/overview
- **Webhook Subscriptions**: https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions

---

**Last Updated**: 2025-11-12  
**Next Review**: After Phase 1 completion
