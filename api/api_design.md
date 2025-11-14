# Unified API Design for Microsoft 365 & Google Workspace Integration

## Overview

This document defines the recommended architecture and design model for a unified API that integrates with both Microsoft 365 (via Microsoft Graph webhooks) and Google Workspace (via Google Pub/Sub Gmail push notifications).

The API is implemented as a **single service**, but with **provider-separated endpoints and provider-specific internal services**, ensuring optimal clarity, security, observability, and maintainability.

### Credentials Model

**Credential = OAuth app configuration for external provider**: A "credential" represents OAuth application settings (client_id, client_secret, scopes) configured by admins for connecting to external providers. One Flovify installation can have multiple credentials per provider.

**Example**: A Flovify instance might have:
- 2 MS365 credentials (production app + testing app, or different Azure AD tenants)
- 3 Google Workspace credentials (different OAuth apps with different scopes)
- Future: Salesforce, Slack, custom OAuth providers

Each credential has:
- OAuth app configuration (stored in Auth Service `auth.credentials`)
- Connected account information (email, external account ID, display name)
- Encrypted OAuth tokens (stored in Auth Service `auth.credential_tokens`)
- Webhook subscriptions (tracked in API Service `api.webhook_subscriptions`)

**Key distinction**: Credentials are OAuth app configurations, not individual connected accounts. After OAuth authorization, a credential becomes "connected" to a specific user account (e.g., john@acme.com).

### System Context

**Flovify complements n8n workflow implementation**:
- **n8n**: High-level workflow orchestration, business logic routing, integration glue
- **Flovify API**: Specialized primitives for AI-powered email/document processing
- **Integration pattern**: n8n workflows call Flovify API endpoints for AI operations
- **Example flow**: n8n triggers on event → calls Flovify to process email → Flovify returns structured data → n8n continues workflow

### Service Ownership

**Auth Service Responsibilities**:
- Store credential definitions (`auth.credentials`)
- Store connected account info (email, external_account_id, display_name)
- Manage OAuth tokens (`auth.credential_tokens`)
- Refresh expired tokens automatically
- Vend tokens to API Service on request (per credential_id)
- Handle OAuth authorization flow and callback

**API Service Responsibilities**:
- Receive webhook notifications (`/api/ms365/webhook`, `/api/googlews/webhook`)
- Track subscription metadata (`api.webhook_subscriptions`)
- Process events via workers
- Fetch messages/data from external systems (using tokens from Auth)
- **Implement business process primitives**: Email parsing, document extraction, AI analysis
- Execute LangGraph workflows
- Expose APIs for n8n workflow consumption

### MS365 Integration Library

**Recommended**: Use **[msgraph-sdk-python](https://github.com/microsoftgraph/msgraph-sdk-python)** - Microsoft's official Graph API SDK for Python.

**Why msgraph-sdk-python**:
- ✅ Official Microsoft SDK with full Graph API coverage
- ✅ Automatic request/response serialization and type safety
- ✅ Built-in retry logic and error handling
- ✅ Batch request support for efficient API calls
- ✅ Fluent API design: `graph_client.users.by_user_id(user_id).messages.get()`
- ✅ Well-maintained with regular updates
- ✅ Integrates with standard Azure.Identity for token management

**Installation**:
```bash
pip install msgraph-sdk azure-identity
```

**Basic usage pattern**:
```python
from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential

# Create credential from our stored OAuth tokens
credential = ClientSecretCredential(
    tenant_id=azure_tenant_id,
    client_id=client_id,
    client_secret=client_secret
)

# Initialize client
graph_client = GraphServiceClient(credential)

# Fetch messages
messages = await graph_client.me.messages.get()

# Fetch specific message
message = await graph_client.me.messages.by_message_id(message_id).get()

# Send email
await graph_client.me.send_mail.post(SendMailPostRequestBody(...))
```

**Alternative considered**: Direct REST API calls via `httpx` - More flexible but requires manual serialization/error handling.

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

## Credential Flow Through System

```
1. Webhook arrives with subscription_id
   ↓
2. API looks up credential_id from api.webhook_subscriptions
   ↓
3. API enqueues (credential_id, event_data) for worker
   ↓
4. Worker requests token from Auth: "Token for credential_id=X"
   ↓
5. Auth returns OAuth token from auth.credential_tokens
   ↓
6. Worker calls external API (MS Graph or Gmail) with credential's token
   ↓
7. Worker processes data, stores in api.* schema with credential_id reference
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
- Creates webhook subscriptions for a specific credential.
- Request includes `credential_id` to identify which MS365 credential to use.
- Requests OAuth token from Auth Service for that credential.
- Stores subscription metadata in `api.webhook_subscriptions`.
- API Service handles subscription renewal before expiry (using token from Auth).

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
- Sets up Gmail watch subscription for a specific credential.
- Request includes `credential_id` to identify which Google Workspace credential to use.
- Requests OAuth token from Auth Service for that credential.
- Persists initial `historyId` and subscription metadata in `api.webhook_subscriptions`.
- API Service handles watch renewal (expires after 7 days, using token from Auth).

---

# 4. Internal Service Layer

## ms365_service
Responsibilities:
- Validate `clientState` from webhook notifications.
- Request OAuth token from Auth Service for specific `credential_id`.
- Use **msgraph-sdk-python** to interact with Microsoft Graph:
  ```python
  from msgraph import GraphServiceClient
  
  # Initialize client with token from Auth
  graph_client = GraphServiceClient(credential_from_auth)
  
  # Fetch message
  message = await graph_client.me.messages.by_message_id(message_id).get()
  ```
- Normalize the message object to internal format.
- **Note**: Does NOT store credentials; always requests tokens from Auth.

---

## googlews_service
Responsibilities:
- Decode Pub/Sub events.
- Request OAuth token from Auth Service for specific `credential_id`.
- Use **google-api-python-client** to interact with Gmail API:
  ```python
  from googleapiclient.discovery import build
  
  # Build service with token from Auth
  service = build('gmail', 'v1', credentials=credentials_from_auth)
  
  # Get history
  history = service.users().history().list(
      userId='me',
      startHistoryId=history_id
  ).execute()
  
  # Fetch message
  message = service.users().messages().get(
      userId='me',
      id=message_id,
      format='full'
  ).execute()
  ```
- Extract message IDs from change logs.
- Normalize fetched message objects to internal format.
- **Note**: Does NOT store credentials; always requests tokens from Auth.

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

### `auth.credentials`
Stores OAuth app configurations and connected account information.

```sql
CREATE TABLE auth.credentials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Identification
  name TEXT NOT NULL UNIQUE,                    -- Slug: "acme-ms365"
  display_name TEXT NOT NULL,                   -- User-friendly: "Acme Corp MS365"
  provider TEXT NOT NULL,                       -- 'ms365' | 'google_workspace'
  
  -- OAuth App Configuration (admin-entered)
  client_id TEXT NOT NULL,
  encrypted_client_secret TEXT NOT NULL,        -- Encrypted with Fernet
  redirect_uri TEXT NOT NULL,                   -- OAuth callback URL
  tenant_id TEXT,                                -- Azure AD Tenant ID (optional, for single-tenant apps)
  authorization_url TEXT NOT NULL,              -- Provider OAuth URL
  token_url TEXT NOT NULL,                      -- Provider token exchange URL
  scopes TEXT[] NOT NULL,                       -- Requested scopes
  
  -- Connected Account Info (populated after OAuth)
  connected_email TEXT,                         -- john@acme.com
  external_account_id TEXT,                     -- Microsoft user ID or Google sub
  connected_display_name TEXT,                  -- John Doe
  
  -- Status tracking
  status TEXT NOT NULL DEFAULT 'pending',       -- 'pending' | 'connected' | 'error'
  error_message TEXT,
  last_connected_at TIMESTAMPTZ,
  
  -- Audit
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  
  -- Indexes
  INDEX idx_credentials_provider (provider),
  INDEX idx_credentials_status (status),
  INDEX idx_credentials_email (connected_email),
  INDEX idx_credentials_external_id (external_account_id),
  INDEX idx_credentials_tenant_id (tenant_id) WHERE tenant_id IS NOT NULL
);
```

**Key fields**:
- `tenant_id`: Azure AD Tenant ID (GUID) for single-tenant MS365 apps. NULL for multi-tenant or Google Workspace.
- `connected_email`: Email address of the connected account (populated after OAuth).
- `external_account_id`: Unique identifier from provider (Microsoft user ID or Google sub).

### `auth.credential_tokens`
Stores encrypted OAuth tokens for each credential.

```sql
CREATE TABLE auth.credential_tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  credential_id UUID NOT NULL REFERENCES auth.credentials(id) ON DELETE CASCADE,
  
  token_type TEXT NOT NULL DEFAULT 'delegated',  -- 'delegated' (future: 'app')
  encrypted_access_token TEXT NOT NULL,          -- Encrypted with Fernet
  encrypted_refresh_token TEXT,                  -- Encrypted with Fernet
  scopes TEXT[],                                  -- Granted scopes
  
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_refreshed_at TIMESTAMPTZ,
  
  -- Only one token per credential
  UNIQUE (credential_id),
  INDEX idx_credential_tokens_credential_id (credential_id),
  INDEX idx_credential_tokens_expires_at (expires_at)
);
```

**Schema version**: Current v0.2.3 (see `auth.schema_registry`)

## API Service Schema (`api.*`)

### `api.webhook_subscriptions`
Tracks active webhook subscriptions per credential.

```sql
CREATE TABLE api.webhook_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  credential_id UUID NOT NULL,                  -- FK to auth.credentials(id)
  provider TEXT NOT NULL,                       -- 'ms365' | 'google_workspace'
  subscription_id TEXT NOT NULL,                -- External subscription ID from MS Graph or Google
  resource TEXT NOT NULL,                       -- Resource being watched (e.g., 'me/messages')
  change_types TEXT[],                          -- ['created', 'updated'] for MS365
  history_id TEXT,                              -- For Google Workspace only (last processed history ID)
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_renewed_at TIMESTAMPTZ,
  
  UNIQUE(provider, subscription_id),
  INDEX idx_webhook_subs_credential_id (credential_id),
  INDEX idx_webhook_subs_expires_at (expires_at)
);
```

**Key changes from tenant model**:
- `credential_id` instead of `tenant_id` - references the OAuth credential used
- Subscription is tied to the credential that has the OAuth token

### `api.webhook_events`
Tracks processed events for idempotency.

```sql
CREATE TABLE api.webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  credential_id UUID NOT NULL,                  -- FK to auth.credentials(id)
  provider TEXT NOT NULL,                       -- 'ms365' | 'google_workspace'
  event_key TEXT NOT NULL,                      -- Idempotency key (subscription_id + resource_id or historyId)
  message_id TEXT,                              -- External message ID after processing
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  correlation_id UUID NOT NULL,
  
  UNIQUE(provider, event_key),
  INDEX idx_webhook_events_credential_id (credential_id),
  INDEX idx_webhook_events_processed_at (processed_at)
);
```

**Note**: Each credential can have multiple subscriptions (different resources), but each subscription is tied to exactly one credential.

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
- API Service **never stores** OAuth credentials or client secrets.
- All tokens are encrypted at rest in Auth Service (`auth.credential_tokens`).
- API requests tokens on-demand: `POST /auth/oauth/internal/credential-token` with `credential_id`.
- Auth Service validates request (requires `X-Service-Token`), refreshes token if needed, returns valid token.
- Short-lived token caching possible in API workers (with expiry check).

**Token vending endpoint**:
```http
POST /auth/oauth/internal/credential-token
X-Service-Token: <shared-secret>
Content-Type: application/json

{
  "credential_id": "uuid"
}

Response:
{
  "access_token": "...",
  "expires_at": "2025-11-14T12:00:00Z",
  "scopes": ["Mail.Read", "Mail.Send"]
}
```

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
credential_id + subscriptionId + resourceId
```

## Google
Use:
```
credential_id + historyId
credential_id + messageId
```

Stored in `api.webhook_events.event_key` with UNIQUE constraint.

Guarantees exact-once processing per credential.

---

# 10. Normalized Internal Event Model

```json
{
  "provider": "ms365" | "google_workspace",
  "credentialId": "uuid",                    // References auth.credentials(id)
  "connectedEmail": "john@acme.com",        // Email from credential.connected_email
  "externalAccountId": "string",             // Microsoft user ID or Google sub
  "eventType": "mail.created",
  "messageId": "string",
  "receivedAt": "timestamp",
  "correlationId": "uuid",
  "raw": {}
}
```

**Key changes**:
- `credentialId` instead of `tenantId` - references the OAuth credential
- `connectedEmail` - the email address associated with the credential
- `externalAccountId` - the provider's unique identifier for the account

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
- Strong security guarantees (OAuth credentials isolated in Auth Service).
- Clear observability and retry patterns.
- Multi-credential support: One installation → Multiple OAuth apps per provider.
- Clear service boundaries: Auth owns credentials/tokens, API owns webhooks and business logic.
- Official SDKs for provider interaction (msgraph-sdk-python, google-api-python-client).
- Easy future refactoring into microservices.
