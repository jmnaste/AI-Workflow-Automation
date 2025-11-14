# API Design Documentation Update Summary

**Date**: 2025-11-14  
**Status**: ✅ Complete

## Changes Made

Updated `api/api_design.md` to align with current **credentials-based architecture** and added **MS365 library recommendations**.

### 1. Terminology Updates

**Before (Obsolete "Tenant" Model)**:
- "Tenant" = connected account in external system
- `auth.tenants` table
- `auth.tenant_tokens` table  
- `tenant_id` foreign keys everywhere

**After (Current "Credentials" Model)**:
- "Credential" = OAuth app configuration
- `auth.credentials` table (with connected account info)
- `auth.credential_tokens` table
- `credential_id` foreign keys everywhere

### 2. Key Conceptual Changes

**Credentials Model** (Section 1):
- Credential = OAuth app configuration (client_id, client_secret, scopes)
- One Flovify instance can have multiple credentials per provider
- After OAuth, credential becomes "connected" to specific user account
- Added distinction: Credentials are configurations, not accounts

**System Flow** (Section 2):
- Updated flow diagram: `tenant_id` → `credential_id`
- Token vending now uses `credential_id`

### 3. MS365 Integration Library (NEW Section)

Added comprehensive recommendation for **msgraph-sdk-python**:
- ✅ Official Microsoft SDK
- ✅ Type-safe, automatic serialization
- ✅ Built-in retry and error handling
- ✅ Fluent API design
- ✅ Batch request support

**Code example added**:
```python
from msgraph import GraphServiceClient
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(tenant_id, client_id, client_secret)
graph_client = GraphServiceClient(credential)

# Fetch messages
messages = await graph_client.me.messages.get()
message = await graph_client.me.messages.by_message_id(message_id).get()
```

**Alternative mentioned**: Direct REST via httpx (more flexible, less convenient)

### 4. API Routes Updates

**Microsoft 365 routes**:
- `/api/ms365/subscriptions`: Now uses `credential_id` instead of `tenant_id`
- Clarified: API Service handles renewal, not Auth

**Google Workspace routes**:
- `/api/googlews/gmail/watch`: Now uses `credential_id`
- Same renewal responsibility clarification

### 5. Service Layer Updates

**ms365_service**:
- Uses msgraph-sdk-python for all Graph API calls
- Added code example showing SDK usage
- Token requests use `credential_id`

**googlews_service**:
- Uses google-api-python-client
- Added code example showing Gmail API usage
- Token requests use `credential_id`

### 6. Database Schema Updates

**auth.credentials table** (complete rewrite):
- Added all actual columns from migration 0008-0011
- Includes: name, display_name, provider, OAuth config
- Includes: connected_email, external_account_id, connected_display_name
- Includes: tenant_id field (Azure AD tenant ID for single-tenant apps)
- Includes: status tracking (pending/connected/error)
- Current schema version: v0.2.3

**auth.credential_tokens table** (updated):
- `credential_id` FK instead of `tenant_id`
- Unique constraint on credential_id (one token per credential)
- Documented encryption (Fernet)

**api.webhook_subscriptions table**:
- `credential_id` FK instead of `tenant_id`
- Index updated

**api.webhook_events table**:
- `credential_id` FK instead of `tenant_id`
- Index updated

### 7. Token Security Section

Updated token vending endpoint documentation:
- Endpoint: `POST /auth/oauth/internal/credential-token`
- Parameter: `credential_id` (not `tenant_id`)
- Added full request/response example

### 8. Idempotency Strategy

Updated event keys:
- `credential_id + subscriptionId + resourceId` (MS365)
- `credential_id + historyId` (Google)

### 9. Normalized Event Model

Updated internal event structure:
```json
{
  "credentialId": "uuid",          // was: tenantId
  "connectedEmail": "email",       // NEW
  "externalAccountId": "string"    // was: userId
}
```

### 10. Benefits Summary

Updated to reflect:
- Multi-credential support (not multi-tenant)
- Official SDK usage
- Auth owns credentials/tokens (clarified)

## Files NOT Updated (Obsolete - To Be Archived)

These files contain old tenant model documentation and should be marked obsolete:

1. **docs/Implementation/ms365_credentials_model.md**
   - Still references old tenant concept
   - Shows migration from tenant → credentials (historical)
   - Should be archived or marked as "superseded by api_design.md"

2. **docs/Implementation/ms365_credentials_implementation.md**
   - References `auth.tenant_tokens` table
   - Old Phase 1/Phase 2 implementation plan
   - Historical value only

3. **docs/Implementation/credentials_refactor_plan.md**
   - Planning document for tenant → credentials migration
   - Already implemented, historical only

**Recommendation**: Move these to `docs/Implementation/archive/` folder with README explaining they document the migration process, not current state.

## Next Steps

### For API Service Implementation:

1. **Install dependencies**:
   ```bash
   pip install msgraph-sdk azure-identity google-api-python-client
   ```

2. **Create token vending client** (API → Auth):
   ```python
   # api/app/services/auth_client.py
   async def get_credential_token(credential_id: str) -> dict:
       response = await httpx.post(
           f"{AUTH_SERVICE_URL}/auth/oauth/internal/credential-token",
           headers={"X-Service-Token": SERVICE_SECRET},
           json={"credential_id": credential_id}
       )
       return response.json()
   ```

3. **Implement MS365 service with msgraph-sdk**:
   ```python
   # api/app/services/ms365_service.py
   from msgraph import GraphServiceClient
   from azure.identity import ClientSecretCredential
   
   async def fetch_message(credential_id: str, message_id: str):
       # Get token from Auth
       token_data = await get_credential_token(credential_id)
       
       # Initialize Graph client
       credential = ClientSecretCredential(...)  # From token_data
       client = GraphServiceClient(credential)
       
       # Fetch message
       return await client.me.messages.by_message_id(message_id).get()
   ```

4. **Create API migrations**:
   - `api/migrations/0001_webhook_subscriptions.sql`
   - `api/migrations/0002_webhook_events.sql`

5. **Implement webhook routes**:
   - `POST /api/ms365/webhook` - receive Graph notifications
   - `POST /api/googlews/webhook` - receive Pub/Sub notifications

## Validation Checklist

- [x] All references to "tenant" concept updated to "credentials"
- [x] Database schema reflects actual implemented tables
- [x] MS365 library recommendation added (msgraph-sdk-python)
- [x] Google library mentioned (google-api-python-client)
- [x] Token vending endpoint documented correctly
- [x] Service ownership clarified (Auth vs API)
- [x] Code examples use official SDKs
- [x] Foreign key references updated (`tenant_id` → `credential_id`)
- [x] Internal event model updated
- [x] Idempotency keys updated

## Documentation Consistency

The following files are now aligned:
- ✅ `.github/copilot-instructions.md` - Updated Nov 13 (credentials model)
- ✅ `auth/README.md` - Updated Nov 13 (OAuth & Credential Management)
- ✅ `webui/ARCHITECTURE.md` - Updated Nov 13 (credential callbacks)
- ✅ `api/api_design.md` - **Updated Nov 14 (this file)**

All core architecture documents now use consistent **credentials-based** terminology.
