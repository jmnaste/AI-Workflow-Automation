# OAuth Webhooks Implementation Guide

## Overview

This document provides the implementation strategy for OAuth integration with Microsoft 365 and Google Workspace. Webhooks are handled by the **Auth service** on a dedicated subdomain (`webhooks.flovify.ca`) to maintain API privacy while enabling external OAuth callbacks.

---

## Architecture Decision

### Why Auth Service Handles Webhooks

**Considered options:**
1. ❌ **API service** — Would break privacy model
2. ❌ **BFF service** — Splits auth logic across services
3. ✅ **Auth service** — Natural domain alignment, already designed for webhook exposure

**Selected: Auth Service**

**Rationale:**
- OAuth token exchange = identity/auth concern
- Auth service owns user credentials and token storage
- Narrow public exposure (only `/webhook/*` paths via Traefik)
- Domain isolation (`webhooks.flovify.ca` separate from `console.flovify.ca`)
- `auth.compose.yml` already has webhook support built-in

---

## Request Flow

### OAuth Flow (User Initiated)

```
1. User clicks "Connect Microsoft" in UI
     ↓
2. Browser → POST https://console.flovify.ca/bff/auth/connect/microsoft
     ↓
3. BFF generates OAuth URL with state token
     ↓
4. Browser → Redirects to Microsoft login
     ↓
5. User authenticates with Microsoft
     ↓
6. Microsoft → Redirects to https://webhooks.flovify.ca/webhook/oauth/microsoft/callback?code=XXX&state=YYY
     ↓
7. Traefik routes to Auth container
     ↓
8. Auth service:
     - Validates state (CSRF protection)
     - Exchanges code for access/refresh tokens (Microsoft API)
     - Encrypts and stores tokens in auth.oauth_tokens table
     - Redirects browser to https://console.flovify.ca/auth/success
     ↓
9. UI shows success message
```

### Webhook Event Flow (Microsoft/Google Initiated)

```
1. Event occurs (email received, file changed, etc.)
     ↓
2. Microsoft/Google → POST https://webhooks.flovify.ca/webhook/events/microsoft
     Headers: X-MS-Signature: <hmac>
     Body: { event data }
     ↓
3. Traefik routes to Auth container
     ↓
4. Auth service:
     - Validates webhook signature
     - Extracts event data
     - Triggers downstream processing (n8n workflow, internal handler)
     - Returns 200 OK
     ↓
5. Microsoft/Google considers event delivered
```

---

## Configuration

### Hostinger VPS Environment Variables

Add to Auth container in Hostinger:

```env
# Existing
TRAEFIK_NETWORK=root_default
DATABASE_URL=postgresql://app_system:PASSWORD@postgres:5432/app_db
SERVICE_SEMVER=0.1.0

# Webhook enablement
AUTH_PUBLIC=true
AUTH_WEBHOOK_HOST=webhooks.flovify.ca
AUTH_WEBHOOK_PATH_PREFIX=/webhook
AUTH_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt

# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-client-id
MICROSOFT_CLIENT_SECRET=your-client-secret
MICROSOFT_WEBHOOK_SECRET=your-webhook-secret

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_WEBHOOK_SECRET=your-webhook-secret
```

### DNS Configuration

Add A record in your domain registrar:

```
Type: A
Name: webhooks
Value: <Your VPS IP>
TTL: 300 (or auto)

Result: webhooks.flovify.ca → <VPS IP>
```

### Microsoft App Registration

1. Go to Azure Portal → App Registrations
2. Create new app or use existing
3. **Redirect URIs:**
   ```
   https://webhooks.flovify.ca/webhook/oauth/microsoft/callback
   ```
4. **API Permissions:**
   - Mail.Read
   - Mail.Send
   - Files.ReadWrite.All
   - Calendars.ReadWrite
   - (Add others as needed)
5. **Certificates & secrets:**
   - Generate client secret → Copy to `MICROSOFT_CLIENT_SECRET`
6. **Webhooks (via Microsoft Graph subscriptions):**
   - Notification URL: `https://webhooks.flovify.ca/webhook/events/microsoft`
   - Generate validation token → Copy to `MICROSOFT_WEBHOOK_SECRET`

### Google Cloud Console

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID
3. **Authorized redirect URIs:**
   ```
   https://webhooks.flovify.ca/webhook/oauth/google/callback
   ```
4. **OAuth consent screen:**
   - Add scopes: gmail, drive, calendar
5. **Download credentials** → Copy client ID and secret
6. **Webhooks (via Push Notifications):**
   - Notification endpoint: `https://webhooks.flovify.ca/webhook/events/google`

---

## Database Schema

### OAuth Tokens Table

```sql
-- auth/migrations/XXXX_oauth_tokens.sql
CREATE TABLE IF NOT EXISTS auth.oauth_tokens (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider VARCHAR(50) NOT NULL, -- 'microsoft' or 'google'
  access_token TEXT NOT NULL,    -- Encrypted
  refresh_token TEXT NOT NULL,   -- Encrypted
  expires_at TIMESTAMPTZ NOT NULL,
  scope TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, provider)
);

CREATE INDEX idx_oauth_tokens_user_provider ON auth.oauth_tokens(user_id, provider);
CREATE INDEX idx_oauth_tokens_expires ON auth.oauth_tokens(expires_at);
```

### OAuth State Table (CSRF Protection)

```sql
-- Temporary state tokens (can use Redis instead)
CREATE TABLE IF NOT EXISTS auth.oauth_states (
  state VARCHAR(64) PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  provider VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_oauth_states_expires ON auth.oauth_states(expires_at);

-- Cleanup expired states (run periodically)
-- DELETE FROM auth.oauth_states WHERE expires_at < NOW();
```

---

## Implementation

### 1. Auth Service: Webhook Routes (FastAPI)

```python
# auth/app/routes/webhooks.py
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import RedirectResponse
import httpx
import hmac
import hashlib
from datetime import datetime, timedelta
from ..config import settings
from ..db import database
from ..crypto import encrypt, decrypt

router = APIRouter(prefix="/webhook", tags=["webhooks"])

@router.get("/oauth/microsoft/callback")
async def microsoft_oauth_callback(
    code: str,
    state: str,
    error: str = None,
    error_description: str = None
):
    """
    Microsoft OAuth callback endpoint.
    Public URL: https://webhooks.flovify.ca/webhook/oauth/microsoft/callback
    """
    if error:
        # Redirect to error page with reason
        return RedirectResponse(
            f"https://console.flovify.ca/auth/error?reason={error}&description={error_description}"
        )
    
    # Validate state token (CSRF protection)
    state_record = await database.fetch_one(
        "SELECT user_id FROM auth.oauth_states WHERE state = :state AND expires_at > NOW()",
        {"state": state}
    )
    
    if not state_record:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    user_id = state_record["user_id"]
    
    # Exchange authorization code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data={
                "client_id": settings.MICROSOFT_CLIENT_ID,
                "client_secret": settings.MICROSOFT_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"https://webhooks.flovify.ca/webhook/oauth/microsoft/callback",
                "grant_type": "authorization_code",
                "scope": "offline_access Mail.Read Mail.Send Files.ReadWrite.All"
            }
        )
    
    if token_response.status_code != 200:
        error_detail = token_response.json().get("error_description", "Token exchange failed")
        return RedirectResponse(f"https://console.flovify.ca/auth/error?reason=token_exchange&description={error_detail}")
    
    tokens = token_response.json()
    
    # Store encrypted tokens
    await database.execute(
        """
        INSERT INTO auth.oauth_tokens (user_id, provider, access_token, refresh_token, expires_at, scope)
        VALUES (:user_id, 'microsoft', :access_token, :refresh_token, :expires_at, :scope)
        ON CONFLICT (user_id, provider)
        DO UPDATE SET
            access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            expires_at = EXCLUDED.expires_at,
            scope = EXCLUDED.scope,
            updated_at = NOW()
        """,
        {
            "user_id": user_id,
            "access_token": encrypt(tokens["access_token"]),
            "refresh_token": encrypt(tokens["refresh_token"]),
            "expires_at": datetime.now() + timedelta(seconds=tokens["expires_in"]),
            "scope": tokens.get("scope")
        }
    )
    
    # Clean up state token
    await database.execute(
        "DELETE FROM auth.oauth_states WHERE state = :state",
        {"state": state}
    )
    
    # Redirect to success page
    return RedirectResponse("https://console.flovify.ca/auth/success?provider=microsoft")


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    error: str = None
):
    """
    Google OAuth callback endpoint.
    Public URL: https://webhooks.flovify.ca/webhook/oauth/google/callback
    """
    if error:
        return RedirectResponse(f"https://console.flovify.ca/auth/error?reason={error}")
    
    # Validate state
    state_record = await database.fetch_one(
        "SELECT user_id FROM auth.oauth_states WHERE state = :state AND expires_at > NOW()",
        {"state": state}
    )
    
    if not state_record:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    user_id = state_record["user_id"]
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": "https://webhooks.flovify.ca/webhook/oauth/google/callback",
                "grant_type": "authorization_code"
            }
        )
    
    if token_response.status_code != 200:
        error_detail = token_response.json().get("error_description", "Token exchange failed")
        return RedirectResponse(f"https://console.flovify.ca/auth/error?reason=token_exchange&description={error_detail}")
    
    tokens = token_response.json()
    
    # Store encrypted tokens
    await database.execute(
        """
        INSERT INTO auth.oauth_tokens (user_id, provider, access_token, refresh_token, expires_at, scope)
        VALUES (:user_id, 'google', :access_token, :refresh_token, :expires_at, :scope)
        ON CONFLICT (user_id, provider)
        DO UPDATE SET
            access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            expires_at = EXCLUDED.expires_at,
            scope = EXCLUDED.scope,
            updated_at = NOW()
        """,
        {
            "user_id": user_id,
            "access_token": encrypt(tokens["access_token"]),
            "refresh_token": encrypt(tokens.get("refresh_token", "")),
            "expires_at": datetime.now() + timedelta(seconds=tokens["expires_in"]),
            "scope": tokens.get("scope")
        }
    )
    
    # Clean up state
    await database.execute(
        "DELETE FROM auth.oauth_states WHERE state = :state",
        {"state": state}
    )
    
    return RedirectResponse("https://console.flovify.ca/auth/success?provider=google")


@router.post("/events/microsoft")
async def microsoft_webhook_event(
    request: Request,
    x_ms_signature: str = Header(None, alias="X-MS-Signature")
):
    """
    Microsoft webhook event receiver.
    Public URL: https://webhooks.flovify.ca/webhook/events/microsoft
    
    Events: email received, calendar updated, file changed, etc.
    """
    body = await request.body()
    
    # Validate signature
    if not x_ms_signature or not validate_microsoft_signature(body, x_ms_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    event = await request.json()
    
    # Handle validation requests from Microsoft
    if event.get("validationToken"):
        return {"validationResponse": event["validationToken"]}
    
    # Process event
    await process_microsoft_event(event)
    
    return {"status": "ok"}


@router.post("/events/google")
async def google_webhook_event(
    request: Request,
    authorization: str = Header(None)
):
    """
    Google webhook event receiver (Push Notifications).
    Public URL: https://webhooks.flovify.ca/webhook/events/google
    """
    # Google uses JWT-based authentication
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")
    
    token = authorization.replace("Bearer ", "")
    
    if not validate_google_webhook_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    event = await request.json()
    
    # Process event
    await process_google_event(event)
    
    return {"status": "ok"}


def validate_microsoft_signature(body: bytes, signature: str) -> bool:
    """Validate webhook signature from Microsoft"""
    secret = settings.MICROSOFT_WEBHOOK_SECRET.encode()
    computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


def validate_google_webhook_token(token: str) -> bool:
    """Validate JWT token from Google webhook"""
    # TODO: Verify JWT signature using Google's public keys
    # from google.auth.transport import requests
    # from google.oauth2 import id_token
    # id_info = id_token.verify_oauth2_token(token, requests.Request())
    # return id_info['aud'] == settings.GOOGLE_CLIENT_ID
    return True  # Placeholder


async def process_microsoft_event(event: dict):
    """Process Microsoft webhook event"""
    # TODO: Implement event processing
    # - Trigger n8n workflow
    # - Update internal state
    # - Send notifications
    pass


async def process_google_event(event: dict):
    """Process Google webhook event"""
    # TODO: Implement event processing
    pass
```

### 2. BFF: OAuth Initiation

```typescript
// bff/src/routes/auth.ts
import express from 'express';
import crypto from 'crypto';
import fetch from 'node-fetch';

const router = express.Router();

router.post('/auth/connect/microsoft', async (req, res) => {
  const userId = req.user.id; // From JWT middleware
  
  // Generate CSRF state token
  const state = crypto.randomBytes(32).toString('hex');
  
  // Store state in Auth service
  await fetch('http://auth:8000/internal/oauth/create-state', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Service-Token': process.env.SERVICE_SECRET
    },
    body: JSON.stringify({
      state,
      user_id: userId,
      provider: 'microsoft',
      expires_in: 600 // 10 minutes
    })
  });
  
  // Build Microsoft OAuth URL
  const authUrl = new URL('https://login.microsoftonline.com/common/oauth2/v2.0/authorize');
  authUrl.searchParams.set('client_id', process.env.MICROSOFT_CLIENT_ID);
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('redirect_uri', 'https://webhooks.flovify.ca/webhook/oauth/microsoft/callback');
  authUrl.searchParams.set('response_mode', 'query');
  authUrl.searchParams.set('scope', 'offline_access Mail.Read Mail.Send Files.ReadWrite.All');
  authUrl.searchParams.set('state', state);
  
  res.json({ authUrl: authUrl.toString() });
});

router.post('/auth/connect/google', async (req, res) => {
  const userId = req.user.id;
  
  const state = crypto.randomBytes(32).toString('hex');
  
  await fetch('http://auth:8000/internal/oauth/create-state', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Service-Token': process.env.SERVICE_SECRET
    },
    body: JSON.stringify({
      state,
      user_id: userId,
      provider: 'google',
      expires_in: 600
    })
  });
  
  const authUrl = new URL('https://accounts.google.com/o/oauth2/v2/auth');
  authUrl.searchParams.set('client_id', process.env.GOOGLE_CLIENT_ID);
  authUrl.searchParams.set('response_type', 'code');
  authUrl.searchParams.set('redirect_uri', 'https://webhooks.flovify.ca/webhook/oauth/google/callback');
  authUrl.searchParams.set('scope', 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive');
  authUrl.searchParams.set('access_type', 'offline');
  authUrl.searchParams.set('prompt', 'consent');
  authUrl.searchParams.set('state', state);
  
  res.json({ authUrl: authUrl.toString() });
});

export default router;
```

### 3. Auth Service: Internal State Management

```python
# auth/app/routes/internal.py
from fastapi import APIRouter, Header, HTTPException
from datetime import datetime, timedelta
import secrets

router = APIRouter(prefix="/internal", tags=["internal"])

@router.post("/oauth/create-state")
async def create_oauth_state(
    data: dict,
    x_service_token: str = Header(...)
):
    """
    Private endpoint: Create OAuth state token.
    Called by BFF when user initiates OAuth flow.
    """
    if x_service_token != settings.SERVICE_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    state = data["state"]
    user_id = data["user_id"]
    provider = data["provider"]
    expires_in = data.get("expires_in", 600)
    
    await database.execute(
        """
        INSERT INTO auth.oauth_states (state, user_id, provider, expires_at)
        VALUES (:state, :user_id, :provider, :expires_at)
        """,
        {
            "state": state,
            "user_id": user_id,
            "provider": provider,
            "expires_at": datetime.now() + timedelta(seconds=expires_in)
        }
    )
    
    return {"status": "ok"}
```

---

## Security Considerations

### 1. Signature Validation (Critical)

**Microsoft:**
```python
def validate_microsoft_signature(body: bytes, signature: str) -> bool:
    secret = settings.MICROSOFT_WEBHOOK_SECRET.encode()
    computed = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)
```

**Google:**
```python
from google.oauth2 import id_token
from google.auth.transport import requests

def validate_google_webhook_token(token: str) -> bool:
    try:
        id_info = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        return id_info['aud'] == settings.GOOGLE_CLIENT_ID
    except ValueError:
        return False
```

### 2. Rate Limiting

Add Traefik middleware:

```yaml
# In auth.compose.yml labels
- traefik.http.middlewares.webhook-ratelimit.ratelimit.average=100
- traefik.http.middlewares.webhook-ratelimit.ratelimit.burst=50
- traefik.http.routers.auth-webhook.middlewares=webhook-ratelimit
```

### 3. IP Allowlisting (Optional)

Microsoft and Google publish their webhook IP ranges. You can allowlist them in Traefik:

```yaml
- traefik.http.middlewares.webhook-ipwhitelist.ipwhitelist.sourcerange=13.107.6.152/31,13.107.18.10/31,35.191.0.0/16
- traefik.http.routers.auth-webhook.middlewares=webhook-ipwhitelist@docker
```

### 4. Token Encryption

```python
# auth/app/crypto.py
from cryptography.fernet import Fernet
import base64

# Generate key: Fernet.generate_key()
# Store in environment: ENCRYPTION_KEY
cipher = Fernet(settings.ENCRYPTION_KEY.encode())

def encrypt(plaintext: str) -> str:
    """Encrypt sensitive data before storing in database"""
    return cipher.encrypt(plaintext.encode()).decode()

def decrypt(ciphertext: str) -> str:
    """Decrypt data when reading from database"""
    return cipher.decrypt(ciphertext.encode()).decode()
```

---

## Testing

### Local Testing (ngrok)

For local development, use ngrok to expose your local Auth service:

```bash
# Start Auth service locally
docker compose -f auth/auth.compose.yml up

# Expose via ngrok
ngrok http 8000

# Use ngrok URL in Microsoft/Google app config
# Redirect URI: https://<random>.ngrok.io/webhook/oauth/microsoft/callback
```

### Manual OAuth Flow Test

```bash
# 1. Get auth URL from BFF
curl -X POST https://console.flovify.ca/bff/auth/connect/microsoft \
  -H "Cookie: session=<your-jwt>" \
  -H "Content-Type: application/json"

# Response: { "authUrl": "https://login.microsoftonline.com/..." }

# 2. Visit authUrl in browser → Login → Get redirected to callback

# 3. Check database
psql -h postgres -U app_root -d app_db
SELECT * FROM auth.oauth_tokens WHERE user_id = 123;
```

### Webhook Event Simulation

```bash
# Simulate Microsoft webhook
curl -X POST https://webhooks.flovify.ca/webhook/events/microsoft \
  -H "Content-Type: application/json" \
  -H "X-MS-Signature: <compute-hmac>" \
  -d '{ "changeType": "created", "resource": "..." }'
```

---

## Monitoring & Logging

### Health Check

```python
# Add to auth/app/routes/webhooks.py
@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoints"""
    return {
        "status": "ok",
        "service": "auth-webhooks",
        "endpoints": [
            "/webhook/oauth/microsoft/callback",
            "/webhook/oauth/google/callback",
            "/webhook/events/microsoft",
            "/webhook/events/google"
        ]
    }
```

### Structured Logging

```python
import logging
logger = logging.getLogger(__name__)

@router.post("/events/microsoft")
async def microsoft_webhook_event(request: Request, ...):
    logger.info({
        "event": "webhook_received",
        "provider": "microsoft",
        "ip": request.client.host,
        "user_agent": request.headers.get("user-agent")
    })
    # ... process event
```

### Metrics to Track

- OAuth callback success/failure rate
- Token refresh success rate
- Webhook event count by type
- Signature validation failures (potential attacks)
- State token validation failures

---

## Migration Checklist

- [ ] Add DNS record: `webhooks.flovify.ca A → <VPS IP>`
- [ ] Set environment variables in Hostinger auth container
- [ ] Run database migrations (oauth_tokens, oauth_states tables)
- [ ] Register app in Microsoft Azure Portal
- [ ] Register app in Google Cloud Console
- [ ] Configure redirect URIs in both platforms
- [ ] Test OAuth flow end-to-end (local with ngrok)
- [ ] Deploy auth service with webhook routes
- [ ] Test production OAuth flow
- [ ] Configure webhook subscriptions in Microsoft Graph
- [ ] Configure push notifications in Google
- [ ] Test webhook event delivery
- [ ] Add monitoring and alerting
- [ ] Document OAuth scopes for users

---

## Future Enhancements

### Short Term
- [ ] Add token refresh logic (when access token expires)
- [ ] Implement webhook retry with exponential backoff
- [ ] Add webhook event queue (Redis/RabbitMQ) for async processing

### Medium Term
- [ ] Support multiple Microsoft/Google accounts per user
- [ ] Add OAuth token revocation endpoint
- [ ] Implement webhook event replay (for debugging)
- [ ] Add OAuth scope management UI

### Long Term
- [ ] Support additional OAuth providers (Slack, Dropbox, etc.)
- [ ] Implement OAuth2 Proof Key for Code Exchange (PKCE) for extra security
- [ ] Add webhook event filtering and routing rules

---

## Summary

This implementation provides:

✅ **Secure OAuth integration** with Microsoft 365 and Google Workspace  
✅ **Private backend architecture** (API never exposed)  
✅ **Domain isolation** (webhooks.flovify.ca separate from console.flovify.ca)  
✅ **Webhook signature validation** (prevent spoofing)  
✅ **Encrypted token storage** (protect user credentials)  
✅ **CSRF protection** (state token validation)  
✅ **Rate limiting** (prevent abuse)  
✅ **Structured logging** (observability)  

The Auth service is the natural home for OAuth logic, and this architecture maintains security while enabling powerful external integrations.

