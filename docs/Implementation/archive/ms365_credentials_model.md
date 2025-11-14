# MS365 Credentials Architecture

**Status**: Documentation Complete - Ready for Refactor Review  
**Created**: 2025-11-12  

## Overview

This document clarifies the **credential-based model** for MS365 integration, inspired by n8n's approach. After reviewing n8n and Microsoft OAuth documentation, we've identified that our "tenant" concept should actually be "credentials" — reusable OAuth configurations entered by admins.

---

## Current vs. Target Model

### ❌ Current Implementation (Incorrect)

**What we built:**
- OAuth credentials (Client ID, Secret, Redirect URI) stored in environment variables
- "Tenant" = one connected MS365 account
- UI allows connecting accounts via OAuth flow
- Each tenant represents one authorized user's email account

**Problem:**
- OAuth app configuration is hardcoded in `.env`
- Admin can't configure multiple OAuth apps
- Doesn't match n8n's reusable credential pattern

### ✅ Target Model (Correct - Like n8n)

**What we should build:**
- Admin creates "credentials" by entering OAuth app config in UI
- Credentials include: Client ID, Client Secret, Redirect URI, Authorization URL, Token URL
- Admin authorizes each credential once (OAuth flow)
- Workflows/API operations reference credentials by ID
- One credential = one MS365 OAuth app configuration with stored tokens

---

## Terminology Clarification

### Credential vs Tenant

**Credential** (what n8n calls it):
- OAuth app configuration entered by admin
- Includes: Client ID, Client Secret, redirect URLs, endpoints
- Represents one Azure App Registration
- Can be reused across multiple workflows/operations
- Example: "Acme Corp MS365 Account"

**Tenant** (Microsoft's term):
- Microsoft 365 organization (e.g., `acme.onmicrosoft.com`)
- Different from our use of "tenant"
- In Microsoft docs, `{tenant}` in URLs refers to Azure AD tenant ID or domain

**Our Confusion:**
- We called credentials "tenants" incorrectly
- Better naming: `auth.credentials` and `auth.credential_tokens`

---

## How It Should Work

### 1. Admin Creates Credential (One-Time Setup)

**In Azure Portal:**
1. Admin goes to Azure Portal → App Registrations
2. Creates new App Registration (e.g., "Flovify Email Integration")
3. Configures redirect URI: `https://console.flovify.ca/auth/oauth/callback`
4. Grants delegated permissions: `Mail.Read`, `Mail.Send`, `User.Read`, `offline_access`
5. Copies Client ID and Client Secret

**In Flovify UI:**
1. Admin navigates to Settings → Credentials
2. Clicks "Create Credential"
3. Selects provider: "Microsoft 365"
4. Fills form:
   ```
   Name: Acme Corp MS365 Account
   Provider: Microsoft 365
   Client ID: 00001111-aaaa-2222-bbbb-3333cccc4444
   Client Secret: sampleCredentia1s
   Redirect URI: https://console.flovify.ca/auth/oauth/callback
   Authorization URL: https://login.microsoftonline.com/common/oauth2/v2.0/authorize
   Access Token URL: https://login.microsoftonline.com/common/oauth2/v2.0/token
   Scopes: offline_access user.read mail.read mail.send
   ```
5. Clicks "Save & Connect"

### 2. Admin Authorizes Credential (One-Time OAuth)

**OAuth Flow:**
1. After clicking "Save & Connect", system redirects to Microsoft login
2. Admin logs in with MS365 account (e.g., `john@acme.com`)
3. Admin grants permissions
4. Microsoft redirects back: `https://console.flovify.ca/auth/oauth/callback?code=...&state=...`
5. Backend exchanges authorization code for tokens
6. Backend stores encrypted tokens in `auth.credential_tokens` table
7. Credential status shows "Connected" in UI

### 3. Workflows Use Credential (Runtime)

**In API Service:**
```python
# Workflow needs to send email via MS365
async def send_email_via_ms365(credential_id: str, to: str, subject: str, body: str):
    # 1. Request token from Auth Service
    token = await auth_client.get_credential_token(credential_id)
    
    # 2. Use token to call Microsoft Graph API
    response = await httpx.post(
        "https://graph.microsoft.com/v1.0/me/sendMail",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}]
            }
        }
    )
    return response.json()
```

**Token Auto-Refresh:**
- Auth Service checks if token expires in < 5 minutes
- If expiring soon, automatically refreshes using refresh token
- Returns fresh access token to API Service
- Workflow never knows about token refresh

---

## Database Schema Changes

### Current Schema (Incorrect)

```sql
-- Current table name
CREATE TABLE auth.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,  -- 'ms365' | 'google_workspace'
    external_account_id TEXT NOT NULL,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(provider, external_account_id)
);

CREATE TABLE auth.tenant_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    -- ... tokens ...
);
```

### Target Schema (Correct)

```sql
-- Rename to credentials
CREATE TABLE auth.credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,  -- User-friendly name: "Acme Corp MS365"
    provider TEXT NOT NULL,  -- 'ms365' | 'google_workspace'
    
    -- OAuth App Configuration (entered by admin)
    client_id TEXT NOT NULL,
    encrypted_client_secret TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    authorization_url TEXT NOT NULL,
    token_url TEXT NOT NULL,
    scopes TEXT[] NOT NULL,
    
    -- Connected Account Info (populated after OAuth)
    external_account_id TEXT,  -- Email address or user ID from provider
    display_name TEXT,
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'connected' | 'error'
    last_connected_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    UNIQUE(provider, client_id)  -- One config per OAuth app
);

CREATE TABLE auth.credential_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID NOT NULL REFERENCES auth.credentials(id) ON DELETE CASCADE,
    token_type TEXT NOT NULL,  -- 'app' | 'delegated'
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    scopes TEXT[],
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_refreshed_at TIMESTAMPTZ,
    INDEX idx_credential_tokens_credential_id (credential_id),
    INDEX idx_credential_tokens_expires_at (expires_at)
);
```

**Key Differences:**
1. Table renamed: `tenants` → `credentials`
2. Added credential configuration fields: `client_id`, `client_secret`, `redirect_uri`, `authorization_url`, `token_url`, `scopes`
3. `name` field for user-friendly identification
4. `status` field to track connection state
5. Foreign key updated: `tenant_id` → `credential_id`

---

## UI Changes

### Current UI (To Refactor)

**Page:** `/admin/tenants`
**Actions:**
- List connected accounts
- "Connect Account" → Provider selection → OAuth redirect

**Issues:**
- No way to enter Client ID/Secret in UI
- Assumes OAuth config in environment variables
- Provider selection happens at connection time

### Target UI

#### 1. Credentials List Page: `/admin/credentials`

**Table Columns:**
- Name (e.g., "Acme Corp MS365")
- Provider (MS365 icon)
- Status (Connected / Pending / Error)
- Connected As (email@acme.com)
- Last Connected
- Actions (Edit, Test Connection, Delete)

**Actions:**
- "Create Credential" button → Opens credential form dialog

#### 2. Create/Edit Credential Dialog

**Form Fields:**
```
Credential Name: [Text Input]
Provider: [Dropdown: Microsoft 365, Google Workspace]

OAuth Configuration:
  Client ID: [Text Input]
  Client Secret: [Password Input]
  Redirect URI: [Text Input with Copy Button]
  Authorization URL: [Text Input with Default]
  Access Token URL: [Text Input with Default]
  Scopes: [Text Area - comma or space separated]

[Cancel] [Save] [Save & Connect]
```

**Behavior:**
- "Save" → Stores credential, status = "pending"
- "Save & Connect" → Stores credential + initiates OAuth flow
- Edit mode → Can update all fields, "Reconnect" button if already connected

#### 3. OAuth Callback Handling

**URL:** `/admin/credentials?oauth_result=success&credential_id=xxx`

**Success Message:**
```
✅ Successfully connected to Microsoft 365!
Connected as: john@acme.com
Credential "Acme Corp MS365" is now ready to use.
```

**Error Message:**
```
❌ Failed to connect to Microsoft 365
Error: Invalid client secret or redirect URI mismatch
[Try Again] [Edit Credential]
```

---

## API Endpoints Changes

### Current Endpoints (To Refactor)

```
GET  /auth/tenants                          # List connected tenants
GET  /auth/oauth/ms365/authorize            # Start OAuth (uses env vars)
GET  /auth/oauth/ms365/callback             # OAuth callback
POST /auth/internal/tenant-token            # Get token for tenant
```

### Target Endpoints

```
# Credential Management
GET    /auth/credentials                    # List all credentials (admin only)
POST   /auth/credentials                    # Create credential (admin only)
GET    /auth/credentials/:id                # Get credential details
PUT    /auth/credentials/:id                # Update credential
DELETE /auth/credentials/:id                # Delete credential
POST   /auth/credentials/:id/test           # Test connection

# OAuth Flow
GET  /auth/oauth/authorize?credential_id=xxx  # Start OAuth for specific credential
GET  /auth/oauth/callback                     # Universal callback (all providers)
POST /auth/oauth/refresh?credential_id=xxx    # Manually refresh token

# Internal API (for API Service)
POST /auth/internal/credential-token        # Get valid token for credential_id
```

**Key Changes:**
1. Credential CRUD endpoints added
2. OAuth endpoints accept `credential_id` parameter
3. Universal callback URL handles all providers
4. Renamed: `tenant-token` → `credential-token`

---

## Environment Variables Changes

### Current (To Remove)

```bash
# These should NOT be in environment variables
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_REDIRECT_URI=...
```

### Target (Keep)

```bash
# These stay - system-level config
OAUTH_ENCRYPTION_KEY=...        # For encrypting tokens
SERVICE_SECRET=...              # For internal API auth
JWT_SECRET=...                  # For user auth
```

**Rationale:**
- OAuth app credentials belong in database, not environment
- Admin can configure multiple OAuth apps per provider
- System-level secrets (encryption keys) stay in environment

---

## Migration Path

### Step 1: Create New Schema

```sql
-- Create new tables
CREATE TABLE auth.credentials (...);
CREATE TABLE auth.credential_tokens (...);

-- Migrate existing data
INSERT INTO auth.credentials (id, name, provider, client_id, ...)
SELECT 
    id,
    'Legacy ' || provider || ' Account',
    provider,
    'from-env-var',  -- Placeholder
    ...
FROM auth.tenants;

-- Copy tokens
INSERT INTO auth.credential_tokens (credential_id, ...)
SELECT tenant_id, ...
FROM auth.tenant_tokens;
```

### Step 2: Update Backend Code

1. Rename all references: `tenant` → `credential`
2. Add credential CRUD endpoints
3. Update OAuth flow to accept `credential_id`
4. Update token retrieval to use credential config from DB

### Step 3: Update Frontend

1. Rename page: `Tenants.tsx` → `Credentials.tsx`
2. Add credential form dialog
3. Update API client: `tenants.ts` → `credentials.ts`
4. Update navigation: "Connected Accounts" → "Credentials"

### Step 4: Migration Script

Admin must manually:
1. Create new credential via UI
2. Enter Client ID and Secret from Azure Portal
3. Authorize credential (OAuth flow)
4. Delete old "legacy" credential entries

---

## Benefits of This Approach

✅ **Matches n8n's proven pattern** - Reusable credentials across workflows
✅ **Multi-app support** - Admin can configure multiple OAuth apps per provider
✅ **No hardcoded secrets** - All credentials in database, not environment
✅ **Better UX** - Clear credential management interface
✅ **Auditable** - Track which credentials are used by which workflows
✅ **Flexible** - Easy to add new providers (Google, Salesforce, etc.)

---

## Decisions Made

1. ✅ **Naming:** Use "Credentials" in UI and code
2. ✅ **Migration:** Drop old `tenants` tables completely - clean slate
3. ✅ **Multiple accounts:** One credential = One MS365 account (one-to-one)
4. ✅ **Credential sharing:** System-wide credentials, referenced by human-readable identifier
5. ✅ **Validation:** Validate if simple, skip if complex - prioritize working flow

## Credential Identification

Credentials can be retrieved by multiple identifiers:

- **Primary:** `credential_id` (UUID) - Internal system reference
- **Human-readable:** `credential_name` (unique) - "acme-ms365" (slugified from display name)
- **Email:** `connected_email` - The MS365 email address authorized (e.g., john@acme.com)
- **External ID:** `external_account_id` - Microsoft's user ID from token claims

**Examples:**
```python
# By ID (workflows)
credential = get_credential(credential_id="123e4567-e89b-12d3-a456-426614174000")

# By name (API calls, human-readable)
credential = get_credential_by_name(name="acme-ms365")

# By email (debugging, admin lookup)
credential = get_credential_by_email(email="john@acme.com")

# By external ID (Microsoft webhook validation)
credential = get_credential_by_external_id(external_id="a1b2c3d4...")
```

---

## Answers to Your Questions

### Q: Rename ms365_tenant_implementation.md file?
**A:** ✅ **Done** - Renamed to `ms365_credentials_implementation.md`

### Q: Refactor migrations to clean tenant pollution?
**A:** ✅ **Yes** - Created `credentials_refactor_plan.md` with:
- Migration 0007: Drop all tenant tables completely
- Migration 0008: Create clean credentials schema
- Version bump: 0.1.3 → 0.2.0 (breaking change)

### Q: Credential retrieval by multiple identifiers?
**A:** ✅ **Supported** - Four lookup methods:
1. **Primary:** `credential_id` (UUID) - Internal reference
2. **Name:** `credential_name` (slug) - Human-readable "acme-ms365"
3. **Email:** `connected_email` - "john@acme.com" 
4. **External ID:** `external_account_id` - Microsoft's user ID

All four indexed for fast lookups.

---

## Next Steps (Ready for Implementation)

1. ✅ **Documentation complete** - Model clarified, decisions made
2. ✅ **Refactor plan created** - See `credentials_refactor_plan.md`
3. **Phase 1:** Apply database migrations (drop tenants, create credentials)
4. **Phase 2:** Refactor backend (Auth Service endpoints)
5. **Phase 3:** Refactor frontend (UI components)
6. **Phase 4:** Test end-to-end with real Azure app
7. **Commit & Deploy:** Update documentation, deploy to VPS
