# Unified API Design for Microsoft 365 & Google Workspace Integration

## Overview

This document defines the recommended architecture and design model for a unified API that integrates with both Microsoft 365 (via Microsoft Graph webhooks) and Google Workspace (via Google Pub/Sub Gmail push notifications).

The API is implemented as a **single service**, but with **provider-separated endpoints and provider-specific internal services**, ensuring optimal clarity, security, observability, and maintainability.

### Tenant Model

**Tenant = Account owned by Flovify instance owner in external system**: A "tenant" represents a specific account (mailbox, workspace user, etc.) that the Flovify instance owner has in an external system. A single Flovify installation can connect to:
- Multiple MS365 accounts (e.g., `john@acme.com`, `john@acme-retail.com`)
- Multiple Google Workspace accounts (different email addresses/domains)
- Future: Multiple Salesforce user accounts, Slack workspaces, etc.

Each tenant has:
- Unique OAuth credentials and tokens (stored in Auth Service)
- Separate webhook subscriptions (tracked in API Service)
- Isolated data and processing pipelines

### System Context

**Flovify complements n8n workflow implementation**:
- **n8n**: High-level workflow orchestration, business logic routing, integration glue
- **Flovify API**: Specialized primitives for AI-powered email/document processing
- **Integration pattern**: n8n workflows call Flovify API endpoints for AI operations
- **Example flow**: n8n triggers on event → calls Flovify to process email → Flovify returns structured data → n8n continues workflow

### Service Ownership

**Auth Service Responsibilities**:
- Store tenant definitions (`auth.tenants`)
- Manage OAuth credentials (`auth.tenant_tokens`)
- Refresh expired tokens
- Renew webhook subscriptions before expiry
- Vend tokens to API Service on request

**API Service Responsibilities**:
- Receive webhook notifications (`/api/ms365/webhook`, `/api/googlews/webhook`)
- Track subscription metadata (`api.webhook_subscriptions`)
- Process events via workers
- Fetch messages/data from external systems (using tokens from Auth)
- **Implement business process primitives**: Email parsing, document extraction, AI analysis
- Execute LangGraph workflows
- Expose APIs for n8n workflow consumption

---

# 1. High-Level Architecture

```
/api
  /ms365
    GET  /webhook        # Graph validation (echo validationToken)
    POST /webhook        # Graph notifications (verify clientState)
    POST /subscriptions  # create/renew/list Graph subscriptions (delegates to Auth)
  /googlews
    POST /webhook        # Pub/Sub push notifications
    POST /gmail/watch    # initiate or renew Gmail "watch" (delegates to Auth)
```

Key attributes:

- Single API deployment.
- Two provider-specific routing namespaces.
- Provider-specific internal service modules.
- Shared core for queueing, auth client, logging, idempotency, and storage.
- Multi-tenant support: One Flovify installation → Many external system tenants.

## Tenant Flow Through System

```
1. Webhook arrives with subscription_id
   ↓
2. API looks up tenant_id from api.webhook_subscriptions
   ↓
3. API enqueues (tenant_id, event_data) for worker
   ↓
4. Worker requests token from Auth: "Token for tenant_id=X"
   ↓
5. Auth returns OAuth token from auth.tenant_tokens
   ↓
6. Worker calls external API (MS Graph or Gmail) with tenant's token
   ↓
7. Worker processes data, stores in api.* schema with tenant_id reference
```

---

# 2. Core Design Principles

### Separation of Concerns
Microsoft 365 and Google Workspace push mechanisms differ significantly in protocol and payload. Handling them independently avoids cross-contamination and reduces complexity.

### Minimal Work in Webhooks
Webhook endpoints must respond immediately (200/204) and offload processing to workers to avoid timeouts and retries.

### Provider-Driven Workflow
Each provider requires a specific follow-up sequence to fetch data:
- MS365: Direct message ID → fetch message.
- Google WS: History ID → resolve changes → fetch messages.

### Unified Envelope Model
Events from both providers are normalized into a consistent internal schema for downstream processing.

---

# 3. API Routes

## 3.1 Microsoft 365

### GET `/api/ms365/webhook`
- Used exclusively for Graph validation.
- Echoes the `validationToken` received in the query params as plain text.

### POST `/api/ms365/webhook`
- Receives Graph change notifications.
- Verifies `clientState` to ensure authenticity.
- Enqueues `{ subscriptionId, resourceId, changeType }`.

### POST `/api/ms365/subscriptions`
- Creates webhook subscriptions for a specific tenant.
- Request includes `tenant_id` to identify which MS365 tenant to subscribe.
- Delegates to Auth Service to obtain OAuth token for that tenant.
- Stores subscription metadata in `api.webhook_subscriptions`.
- Auth Service handles subscription renewal before expiry.

---

## 3.2 Google Workspace

### POST `/api/googlews/webhook`
- Receives Pub/Sub push notifications.
- Optionally validates Google-signed JWT (audience check).
- Decodes Base64 payload to extract:
  - `emailAddress`
  - `historyId`
- Responds with `204 No Content`.

### POST `/api/googlews/gmail/watch`
- Sets up Gmail watch subscription for a specific tenant.
- Request includes `tenant_id` to identify which Google Workspace tenant.
- Delegates to Auth Service to obtain OAuth token for that tenant.
- Persists initial `historyId` and subscription metadata in `api.webhook_subscriptions`.
- Auth Service handles watch renewal (expires after 7 days).

---

# 4. Internal Service Layer

## ms365_service
Responsibilities:
- Validate `clientState` from webhook notifications.
- Request OAuth token from Auth Service for specific `tenant_id`.
- Fetch message content using token:
  ```
  GET /me/messages/{messageId}
  Authorization: Bearer {token_from_auth}
  ```
- Normalize the message object.
- **Note**: Does NOT store credentials; always requests from Auth.

---

## googlews_service
Responsibilities:
- Decode Pub/Sub events.
- Request OAuth token from Auth Service for specific `tenant_id`.
- Call Gmail History API using token:
  ```
  GET /gmail/v1/users/me/history?startHistoryId={historyId}
  Authorization: Bearer {token_from_auth}
  ```
- Extract message IDs from change logs.
- Fetch messages using token:
  ```
  GET /gmail/v1/users/me/messages/{id}?format=full
  Authorization: Bearer {token_from_auth}
  ```
- Normalize fetched message objects.
- **Note**: Does NOT store credentials; always requests from Auth.

---

# 5. Worker Responsibilities

## ms365_worker
- Consume enqueued events.
- Fetch message metadata and body.
- Normalize and persist.
- Retry with backoff for Graph errors.

---

## googlews_worker
- Consume `(emailAddress, historyId)`.
- Resolve changes via History API.
- Deduplicate message IDs.
- Fetch each message.
- Normalize and persist.

---

# 6. Database Schema

## Auth Service Schema (`auth.*`)

### `auth.tenants`
Stores accounts owned by Flovify instance owner in external systems.

```sql
CREATE TABLE auth.tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,  -- 'ms365' | 'googlews' | 'salesforce' | ...
  external_account_id TEXT NOT NULL,  -- Email address, user ID, etc.
  external_tenant_id TEXT,  -- Optional: MS tenant ID, Google domain (for grouping)
  display_name TEXT NOT NULL,  -- 'John @ Acme HQ', 'John @ Acme Retail', etc.
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(provider, external_account_id)
);
```

**Note**: `external_account_id` is the unique identifier for the account (e.g., email address). `external_tenant_id` is optional metadata for organizational grouping.

### `auth.tenant_tokens`
Stores OAuth credentials for each tenant.

```sql
CREATE TABLE auth.tenant_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
  token_type TEXT NOT NULL,  -- 'app' | 'delegated'
  encrypted_access_token TEXT NOT NULL,  -- Encrypted with app key
  encrypted_refresh_token TEXT,  -- Encrypted with app key
  scopes TEXT[],  -- Array of granted scopes
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_refreshed_at TIMESTAMPTZ,
  INDEX idx_tenant_tokens_tenant_id (tenant_id),
  INDEX idx_tenant_tokens_expires_at (expires_at)
);
```

## API Service Schema (`api.*`)

### `api.webhook_subscriptions`
Tracks active webhook subscriptions per tenant.

```sql
CREATE TABLE api.webhook_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,  -- FK to auth.tenants(id)
  provider TEXT NOT NULL,  -- 'ms365' | 'googlews'
  subscription_id TEXT NOT NULL,  -- External subscription ID
  resource TEXT NOT NULL,  -- Resource being watched (e.g., 'me/messages')
  change_types TEXT[],  -- ['created', 'updated'] for MS365
  history_id TEXT,  -- For Google Workspace only
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_renewed_at TIMESTAMPTZ,
  UNIQUE(provider, subscription_id),
  INDEX idx_webhook_subs_tenant_id (tenant_id),
  INDEX idx_webhook_subs_expires_at (expires_at)
);
```

### `api.webhook_events`
Tracks processed events for idempotency.

```sql
CREATE TABLE api.webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  provider TEXT NOT NULL,
  event_key TEXT NOT NULL,  -- Idempotency key (subscription_id + resource_id or historyId)
  message_id TEXT,  -- External message ID after processing
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  correlation_id UUID NOT NULL,
  UNIQUE(provider, event_key),
  INDEX idx_webhook_events_tenant_id (tenant_id),
  INDEX idx_webhook_events_processed_at (processed_at)
);
```

## Migration Strategy

- Auth schema changes: `auth/migrations/00XX_tenant_model.sql`
- API schema changes: `api/migrations/00XX_webhook_subscriptions.sql`
- Both services maintain separate migration sequences
- Version registry updated per service after migration

---

# 7. Security Model

## Microsoft 365
- Validation uses GET echo of `validationToken`.
- Notifications are integrity-protected via `clientState`.
- Webhook contains no sensitive data.
- Fetch requires OAuth authorization (token obtained from Auth Service per tenant).

---

## Google Workspace
- Push events come via Pub/Sub intermediary.
- Optional JWT signature verification ensures authenticity.
- Payload contains only history IDs.
- Data extracted only after authenticated API calls (token obtained from Auth Service per tenant).

---

## Token Security
- API Service **never stores** OAuth credentials.
- All tokens are encrypted at rest in Auth Service (`auth.tenant_tokens`).
- API requests tokens on-demand: `POST /auth/internal/tokens` with `tenant_id`.
- Auth Service validates request, refreshes token if needed, returns valid token.
- Short-lived token caching possible in API workers (with expiry check).

---

# 7. Observability & Monitoring

Recommended metrics:

- `ms365_webhook_status`
- `googlews_webhook_status`
- `ms365_fetch_latency`
- `googlews_history_latency`
- Worker error counts
- Subscription renewal failures

Recommended logs:

- Webhook reception
- Validation outcomes
- Queue enqueue/dequeue
- API call failures

---

# 9. Idempotency Strategy

## Microsoft
Use:
```
tenant_id + subscriptionId + resourceId
```

## Google
Use:
```
tenant_id + historyId
tenant_id + messageId
```

Stored in `api.webhook_events.event_key` with UNIQUE constraint.

Guarantees exact-once processing per tenant.

---

# 10. Normalized Internal Event Model

```
{
  "provider": "ms365" | "googlews",
  "tenantId": "uuid",  // References auth.tenants(id)
  "externalTenantId": "string",  // MS tenant ID or Google domain
  "userId": "string",  // User within that external tenant
  "eventType": "mail.created",
  "messageId": "string",
  "receivedAt": "timestamp",
  "correlationId": "uuid",
  "raw": {}
}
```

**Note**: `tenantId` is the Flovify internal UUID for the external tenant. This allows consistent references across all services.

---

# 11. Directory Layout Example

```
app/
  routers/
    ms365.py
    googlews.py
  services/
    ms365_service.py
    googlews_service.py
  workers/
    ms365_worker.py
    googlews_worker.py
  core/
    queue.py
    http.py
    auth.py
    logging.py
    idempotency.py
    models.py
```

---

# 12. Deployment Considerations

- One container or service instance.
- Two route groups (/ms365 and /googlews).
- Reverse proxy or API gateway can route based on path.
- Scalable workers per provider.

Optional scaling strategy:
- Split into two microservices later without changing public contracts.

---

# 13. Benefits Summary

- Unified, elegant architecture.
- Strict separation of provider logic.
- Clean extensibility (e.g., add Outlook, Drive, Slack).
- Strong security guarantees (credentials isolated in Auth Service).
- Clear observability and retry patterns.
- Multi-tenant support: One installation → Many external systems.
- Clear service boundaries: Auth owns credentials, API owns webhooks and business logic.
- Easy future refactoring into microservices.
