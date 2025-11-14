# Credentials Refactor Plan

**Status**: Ready for Implementation  
**Created**: 2025-11-12  
**Target**: Replace "tenant" concept with "credentials"

---

## Decisions Summary

✅ **Terminology:** "Credentials" (not "Connections" or "Tenants")  
✅ **Scope:** System-wide credentials, referenced by human-readable name  
✅ **Model:** One credential = One MS365 account  
✅ **Migration:** Drop all `tenant` tables completely - start clean  
✅ **Validation:** Simple validation only (e.g., non-empty fields)  

---

## Phase 1: Clean Database Migration

### Drop Old Tenant Tables

**File:** `auth/migrations/0007_drop_tenants.sql`

```sql
-- Drop old tenant tables completely
DROP TABLE IF EXISTS auth.tenant_tokens CASCADE;
DROP TABLE IF EXISTS auth.tenants CASCADE;

-- Update migration history
INSERT INTO auth.migration_history (schema_name, file_seq, name, description, applied_at)
VALUES ('auth', 7, '0007_drop_tenants', 'Drop old tenant tables', now());
```

### Create New Credentials Tables

**File:** `auth/migrations/0008_credentials.sql`

```sql
-- Credentials table (OAuth app configurations + connected accounts)
CREATE TABLE auth.credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identification
    name TEXT NOT NULL UNIQUE,  -- Human-readable: "acme-ms365" (slugified)
    display_name TEXT NOT NULL,  -- User-friendly: "Acme Corp MS365"
    provider TEXT NOT NULL,      -- 'ms365' | 'google_workspace'
    
    -- OAuth App Configuration (entered by admin)
    client_id TEXT NOT NULL,
    encrypted_client_secret TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    authorization_url TEXT NOT NULL,
    token_url TEXT NOT NULL,
    scopes TEXT[] NOT NULL,
    
    -- Connected Account Info (populated after OAuth)
    connected_email TEXT,           -- john@acme.com
    external_account_id TEXT,       -- Microsoft's user ID
    connected_display_name TEXT,    -- John Doe
    
    -- Status
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'connected' | 'error'
    error_message TEXT,
    last_connected_at TIMESTAMPTZ,
    
    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by UUID REFERENCES auth.users(id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Indexes for lookups
    CONSTRAINT credentials_name_unique UNIQUE (name),
    CONSTRAINT credentials_provider_clientid_unique UNIQUE (provider, client_id)
);

CREATE INDEX idx_credentials_provider ON auth.credentials(provider);
CREATE INDEX idx_credentials_status ON auth.credentials(status);
CREATE INDEX idx_credentials_email ON auth.credentials(connected_email);
CREATE INDEX idx_credentials_external_id ON auth.credentials(external_account_id);

-- Credential tokens (access/refresh tokens)
CREATE TABLE auth.credential_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID NOT NULL REFERENCES auth.credentials(id) ON DELETE CASCADE,
    
    token_type TEXT NOT NULL,  -- 'delegated' (future: 'app')
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    scopes TEXT[],
    
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_refreshed_at TIMESTAMPTZ,
    
    -- Only one active token per credential
    CONSTRAINT credential_tokens_unique UNIQUE (credential_id)
);

CREATE INDEX idx_credential_tokens_credential_id ON auth.credential_tokens(credential_id);
CREATE INDEX idx_credential_tokens_expires_at ON auth.credential_tokens(expires_at);

-- Grant permissions
GRANT USAGE ON SCHEMA auth TO app_root;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA auth TO app_root;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA auth TO app_root;

-- Update migration history
INSERT INTO auth.migration_history (schema_name, file_seq, name, description, applied_at)
VALUES ('auth', 8, '0008_credentials', 'Create credentials and credential_tokens tables', now());

-- Update schema registry
UPDATE auth.schema_registry 
SET semver = '0.2.0', ts_key = extract(epoch from now()), applied_at = now()
WHERE service = 'auth';

INSERT INTO auth.schema_registry_history (service, semver, ts_key, applied_at)
VALUES ('auth', '0.2.0', extract(epoch from now()), now());
```

**Version Bump:** `0.1.3` → `0.2.0` (breaking change - dropped tenant tables)

---

## Phase 2: Backend Refactor

### File Renames

```bash
# Auth service
auth/app/routers/oauth.py → auth/app/routers/credentials_oauth.py
auth/app/services/oauth.py → auth/app/services/credentials.py

# Or keep oauth.py name, just update internal references
```

### Update Auth Service Endpoints

**File:** `auth/app/routers/credentials.py` (NEW)

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
import re

router = APIRouter(prefix="/auth/credentials", tags=["credentials"])

class CreateCredentialRequest(BaseModel):
    display_name: str
    provider: str  # 'ms365' | 'google_workspace'
    client_id: str
    client_secret: str
    redirect_uri: str
    authorization_url: str
    token_url: str
    scopes: List[str]

class CredentialResponse(BaseModel):
    id: str
    name: str
    display_name: str
    provider: str
    status: str
    connected_email: Optional[str]
    connected_display_name: Optional[str]
    last_connected_at: Optional[str]
    created_at: str

def slugify(text: str) -> str:
    """Convert display name to URL-safe slug"""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text

@router.post("", response_model=CredentialResponse)
async def create_credential(req: CreateCredentialRequest, user=Depends(verify_admin_jwt)):
    """Create new credential configuration (admin only)"""
    # Generate slug from display_name
    name = slugify(req.display_name)
    
    # Check uniqueness
    existing = await db.fetchrow(
        "SELECT id FROM auth.credentials WHERE name = $1", name
    )
    if existing:
        raise HTTPException(400, f"Credential name '{name}' already exists")
    
    # Encrypt client secret
    encrypted_secret = encrypt_token(req.client_secret)
    
    # Insert credential
    credential_id = await db.fetchval(
        """
        INSERT INTO auth.credentials 
        (name, display_name, provider, client_id, encrypted_client_secret, 
         redirect_uri, authorization_url, token_url, scopes, created_by)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        RETURNING id
        """,
        name, req.display_name, req.provider, req.client_id, encrypted_secret,
        req.redirect_uri, req.authorization_url, req.token_url, req.scopes, user['id']
    )
    
    return await get_credential(credential_id)

@router.get("", response_model=List[CredentialResponse])
async def list_credentials(user=Depends(verify_admin_jwt)):
    """List all credentials (admin only)"""
    rows = await db.fetch(
        """
        SELECT id, name, display_name, provider, status, 
               connected_email, connected_display_name,
               last_connected_at, created_at
        FROM auth.credentials
        ORDER BY created_at DESC
        """
    )
    return [dict(row) for row in rows]

@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(credential_id: str, user=Depends(verify_admin_jwt)):
    """Get credential by ID (admin only)"""
    row = await db.fetchrow(
        """
        SELECT id, name, display_name, provider, status,
               connected_email, connected_display_name,
               last_connected_at, created_at
        FROM auth.credentials WHERE id = $1
        """,
        credential_id
    )
    if not row:
        raise HTTPException(404, "Credential not found")
    return dict(row)

@router.get("/by-name/{name}", response_model=CredentialResponse)
async def get_credential_by_name(name: str, user=Depends(verify_admin_jwt)):
    """Get credential by name (admin only)"""
    row = await db.fetchrow(
        """
        SELECT id, name, display_name, provider, status,
               connected_email, connected_display_name,
               last_connected_at, created_at
        FROM auth.credentials WHERE name = $1
        """,
        name
    )
    if not row:
        raise HTTPException(404, f"Credential '{name}' not found")
    return dict(row)

@router.delete("/{credential_id}")
async def delete_credential(credential_id: str, user=Depends(verify_admin_jwt)):
    """Delete credential (admin only)"""
    result = await db.execute(
        "DELETE FROM auth.credentials WHERE id = $1",
        credential_id
    )
    if result == "DELETE 0":
        raise HTTPException(404, "Credential not found")
    return {"message": "Credential deleted"}

@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str,
    req: CreateCredentialRequest,
    user=Depends(verify_admin_jwt)
):
    """Update credential configuration (admin only)"""
    encrypted_secret = encrypt_token(req.client_secret)
    
    await db.execute(
        """
        UPDATE auth.credentials
        SET display_name = $2, client_id = $3, encrypted_client_secret = $4,
            redirect_uri = $5, authorization_url = $6, token_url = $7,
            scopes = $8, updated_at = now()
        WHERE id = $1
        """,
        credential_id, req.display_name, req.client_id, encrypted_secret,
        req.redirect_uri, req.authorization_url, req.token_url, req.scopes
    )
    
    return await get_credential(credential_id)
```

### Update OAuth Flow

**File:** `auth/app/routers/credentials_oauth.py`

```python
@router.get("/auth/oauth/authorize")
async def start_oauth_flow(credential_id: str, user=Depends(verify_admin_jwt)):
    """Start OAuth flow for specific credential"""
    # Load credential config from database
    cred = await db.fetchrow(
        """
        SELECT client_id, authorization_url, redirect_uri, scopes
        FROM auth.credentials WHERE id = $1
        """,
        credential_id
    )
    if not cred:
        raise HTTPException(404, "Credential not found")
    
    # Generate CSRF state token
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "credential_id": credential_id,
        "expires_at": datetime.now() + timedelta(minutes=10)
    }
    
    # Build OAuth URL using credential config
    params = {
        "client_id": cred['client_id'],
        "response_type": "code",
        "redirect_uri": cred['redirect_uri'],
        "scope": " ".join(cred['scopes']),
        "state": state,
        "prompt": "consent"
    }
    oauth_url = f"{cred['authorization_url']}?{urlencode(params)}"
    
    return RedirectResponse(oauth_url)

@router.get("/auth/oauth/callback")
async def oauth_callback(code: str, state: str):
    """Universal OAuth callback (all providers)"""
    # Validate state
    if state not in oauth_states:
        raise HTTPException(400, "Invalid state token")
    
    state_data = oauth_states.pop(state)
    credential_id = state_data['credential_id']
    
    # Load credential config
    cred = await db.fetchrow(
        """
        SELECT id, provider, client_id, encrypted_client_secret,
               redirect_uri, token_url
        FROM auth.credentials WHERE id = $1
        """,
        credential_id
    )
    
    client_secret = decrypt_token(cred['encrypted_client_secret'])
    
    # Exchange code for tokens
    token_response = await exchange_code_for_tokens(
        provider=cred['provider'],
        code=code,
        client_id=cred['client_id'],
        client_secret=client_secret,
        redirect_uri=cred['redirect_uri'],
        token_url=cred['token_url']
    )
    
    # Get user info from provider
    user_info = await get_user_info(cred['provider'], token_response['access_token'])
    
    # Update credential with connected account info
    await db.execute(
        """
        UPDATE auth.credentials
        SET status = 'connected',
            connected_email = $2,
            external_account_id = $3,
            connected_display_name = $4,
            last_connected_at = now()
        WHERE id = $1
        """,
        credential_id,
        user_info['email'],
        user_info['id'],
        user_info['display_name']
    )
    
    # Store tokens
    await store_credential_tokens(credential_id, token_response)
    
    # Redirect to UI success page
    return RedirectResponse(f"{UI_BASE_URL}/admin/credentials?oauth_result=success&credential_id={credential_id}")
```

### Internal Token Endpoint

**File:** `auth/app/routers/credentials_oauth.py`

```python
@router.post("/auth/internal/credential-token")
async def get_credential_token(
    credential_id: str,
    service_token: str = Header(..., alias="X-Service-Token")
):
    """Get valid access token for credential (internal API only)"""
    # Validate service-to-service auth
    if service_token != os.getenv("SERVICE_SECRET"):
        raise HTTPException(401, "Invalid service token")
    
    # Get token (with auto-refresh)
    token_data = await get_valid_credential_token(credential_id)
    
    return {
        "access_token": token_data['access_token'],
        "expires_at": token_data['expires_at'].isoformat()
    }

async def get_valid_credential_token(credential_id: str) -> dict:
    """Get valid token, refreshing if needed"""
    token_row = await db.fetchrow(
        """
        SELECT encrypted_access_token, encrypted_refresh_token, expires_at
        FROM auth.credential_tokens WHERE credential_id = $1
        """,
        credential_id
    )
    
    if not token_row:
        raise HTTPException(404, "No token found for credential")
    
    # Check if token expires in < 5 minutes
    if token_row['expires_at'] < datetime.now() + timedelta(minutes=5):
        # Refresh token
        cred = await db.fetchrow(
            "SELECT provider, encrypted_client_secret, token_url FROM auth.credentials WHERE id = $1",
            credential_id
        )
        
        refresh_token = decrypt_token(token_row['encrypted_refresh_token'])
        client_secret = decrypt_token(cred['encrypted_client_secret'])
        
        new_tokens = await refresh_access_token(
            provider=cred['provider'],
            refresh_token=refresh_token,
            client_secret=client_secret,
            token_url=cred['token_url']
        )
        
        # Update stored tokens
        await db.execute(
            """
            UPDATE auth.credential_tokens
            SET encrypted_access_token = $2,
                expires_at = $3,
                last_refreshed_at = now()
            WHERE credential_id = $1
            """,
            credential_id,
            encrypt_token(new_tokens['access_token']),
            datetime.now() + timedelta(seconds=new_tokens['expires_in'])
        )
        
        return {
            "access_token": new_tokens['access_token'],
            "expires_at": datetime.now() + timedelta(seconds=new_tokens['expires_in'])
        }
    
    # Token still valid
    return {
        "access_token": decrypt_token(token_row['encrypted_access_token']),
        "expires_at": token_row['expires_at']
    }
```

---

## Phase 3: Frontend Refactor

### File Renames

```bash
webui/ui/src/pages/admin/Tenants.tsx → Credentials.tsx
webui/ui/src/components/admin/ConnectTenantDialog.tsx → CreateCredentialDialog.tsx
webui/ui/src/lib/api/tenants.ts → credentials.ts
```

### Update Navigation

**File:** `webui/ui/src/shell/Navigation.tsx`

```tsx
// Change from:
{ text: 'Connected Accounts', icon: <CloudIcon />, path: '/admin/tenants' }

// To:
{ text: 'Credentials', icon: <KeyIcon />, path: '/admin/credentials' }
```

### Credentials Page

**File:** `webui/ui/src/pages/admin/Credentials.tsx`

```tsx
import React, { useEffect, useState } from 'react';
import {
  Box, Button, Chip, IconButton, Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow, Typography, Alert
} from '@mui/material';
import { Add as AddIcon, Delete as DeleteIcon, Edit as EditIcon, Key as KeyIcon } from '@mui/icons-material';
import { CreateCredentialDialog } from '../../components/admin/CreateCredentialDialog';
import { ConfirmDialog } from '../../components/admin/ConfirmDialog';
import * as credentialsApi from '../../lib/api/credentials';

interface Credential {
  id: string;
  name: string;
  display_name: string;
  provider: string;
  status: string;
  connected_email?: string;
  connected_display_name?: string;
  last_connected_at?: string;
  created_at: string;
}

export const Credentials: React.FC = () => {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [credentialToDelete, setCredentialToDelete] = useState<Credential | null>(null);
  const [oauthResult, setOauthResult] = useState<string | null>(null);

  useEffect(() => {
    loadCredentials();
    
    // Check for OAuth callback result
    const params = new URLSearchParams(window.location.search);
    const result = params.get('oauth_result');
    if (result) {
      setOauthResult(result);
      // Clear URL params
      window.history.replaceState({}, '', '/admin/credentials');
    }
  }, []);

  const loadCredentials = async () => {
    try {
      setLoading(true);
      const data = await credentialsApi.listCredentials();
      setCredentials(data);
      setError(null);
    } catch (err) {
      setError('Failed to load credentials');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (credential: Credential) => {
    setCredentialToDelete(credential);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!credentialToDelete) return;
    
    try {
      await credentialsApi.deleteCredential(credentialToDelete.id);
      setDeleteDialogOpen(false);
      setCredentialToDelete(null);
      await loadCredentials();
    } catch (err) {
      console.error('Failed to delete credential:', err);
      alert('Failed to delete credential');
    }
  };

  const handleCreateSuccess = () => {
    setCreateDialogOpen(false);
    loadCredentials();
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">Credentials</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Credential
        </Button>
      </Box>

      {oauthResult === 'success' && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setOauthResult(null)}>
          Successfully connected to provider! Credential is now ready to use.
        </Alert>
      )}

      {oauthResult === 'error' && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setOauthResult(null)}>
          Failed to connect to provider. Please try again or check your configuration.
        </Alert>
      )}

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Provider</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Connected As</TableCell>
              <TableCell>Last Connected</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {credentials.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <KeyIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                  <Typography variant="body1" color="text.secondary">
                    No credentials configured yet
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Create a credential to connect to Microsoft 365, Google Workspace, or other services
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            
            {credentials.map((cred) => (
              <TableRow key={cred.id}>
                <TableCell>
                  <Typography variant="body1" fontWeight="medium">{cred.display_name}</Typography>
                  <Typography variant="caption" color="text.secondary">{cred.name}</Typography>
                </TableCell>
                <TableCell>
                  <Chip label={cred.provider === 'ms365' ? 'Microsoft 365' : cred.provider} size="small" />
                </TableCell>
                <TableCell>
                  <Chip
                    label={cred.status}
                    size="small"
                    color={cred.status === 'connected' ? 'success' : cred.status === 'error' ? 'error' : 'default'}
                  />
                </TableCell>
                <TableCell>
                  {cred.connected_email ? (
                    <>
                      <Typography variant="body2">{cred.connected_display_name}</Typography>
                      <Typography variant="caption" color="text.secondary">{cred.connected_email}</Typography>
                    </>
                  ) : (
                    <Typography variant="body2" color="text.secondary">Not connected</Typography>
                  )}
                </TableCell>
                <TableCell>
                  {cred.last_connected_at ? new Date(cred.last_connected_at).toLocaleString() : '—'}
                </TableCell>
                <TableCell align="right">
                  <IconButton size="small" onClick={() => handleDelete(cred)}>
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <CreateCredentialDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSuccess={handleCreateSuccess}
      />

      <ConfirmDialog
        open={deleteDialogOpen}
        title="Delete Credential"
        message={`Are you sure you want to delete "${credentialToDelete?.display_name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        confirmColor="error"
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDeleteConfirm}
      />
    </Box>
  );
};
```

### Create Credential Dialog

**File:** `webui/ui/src/components/admin/CreateCredentialDialog.tsx`

```tsx
import React, { useState } from 'react';
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, MenuItem, Typography, Box, Alert
} from '@mui/material';
import * as credentialsApi from '../../lib/api/credentials';

interface CreateCredentialDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const PROVIDERS = [
  { value: 'ms365', label: 'Microsoft 365', defaultAuthUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize', defaultTokenUrl: 'https://login.microsoftonline.com/common/oauth2/v2.0/token' },
  { value: 'google_workspace', label: 'Google Workspace', defaultAuthUrl: 'https://accounts.google.com/o/oauth2/v2/auth', defaultTokenUrl: 'https://oauth2.googleapis.com/token' },
];

export const CreateCredentialDialog: React.FC<CreateCredentialDialogProps> = ({
  open, onClose, onSuccess
}) => {
  const [displayName, setDisplayName] = useState('');
  const [provider, setProvider] = useState('ms365');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [redirectUri, setRedirectUri] = useState('https://console.flovify.ca/auth/oauth/callback');
  const [authorizationUrl, setAuthorizationUrl] = useState(PROVIDERS[0].defaultAuthUrl);
  const [tokenUrl, setTokenUrl] = useState(PROVIDERS[0].defaultTokenUrl);
  const [scopes, setScopes] = useState('offline_access user.read mail.read mail.send');
  const [connectNow, setConnectNow] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleProviderChange = (newProvider: string) => {
    setProvider(newProvider);
    const providerConfig = PROVIDERS.find(p => p.value === newProvider);
    if (providerConfig) {
      setAuthorizationUrl(providerConfig.defaultAuthUrl);
      setTokenUrl(providerConfig.defaultTokenUrl);
    }
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError(null);

      const scopeList = scopes.split(/[\s,]+/).filter(s => s.length > 0);

      const credential = await credentialsApi.createCredential({
        display_name: displayName,
        provider,
        client_id: clientId,
        client_secret: clientSecret,
        redirect_uri: redirectUri,
        authorization_url: authorizationUrl,
        token_url: tokenUrl,
        scopes: scopeList
      });

      if (connectNow) {
        // Start OAuth flow
        const oauthUrl = await credentialsApi.startOAuthFlow(credential.id);
        window.location.href = oauthUrl;
      } else {
        onSuccess();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create credential');
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Create Credential</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          {error && <Alert severity="error">{error}</Alert>}

          <TextField
            label="Display Name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            helperText="User-friendly name (e.g., 'Acme Corp MS365')"
            required
            fullWidth
          />

          <TextField
            select
            label="Provider"
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            required
            fullWidth
          >
            {PROVIDERS.map((p) => (
              <MenuItem key={p.value} value={p.value}>{p.label}</MenuItem>
            ))}
          </TextField>

          <Typography variant="subtitle2" sx={{ mt: 2 }}>OAuth Configuration</Typography>

          <TextField
            label="Client ID"
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            helperText="From Azure App Registration or Google Cloud Console"
            required
            fullWidth
          />

          <TextField
            label="Client Secret"
            type="password"
            value={clientSecret}
            onChange={(e) => setClientSecret(e.target.value)}
            helperText="Keep this secure - it will be encrypted"
            required
            fullWidth
          />

          <TextField
            label="Redirect URI"
            value={redirectUri}
            onChange={(e) => setRedirectUri(e.target.value)}
            helperText="Must match the URI registered in OAuth app"
            required
            fullWidth
          />

          <TextField
            label="Authorization URL"
            value={authorizationUrl}
            onChange={(e) => setAuthorizationUrl(e.target.value)}
            required
            fullWidth
          />

          <TextField
            label="Token URL"
            value={tokenUrl}
            onChange={(e) => setTokenUrl(e.target.value)}
            required
            fullWidth
          />

          <TextField
            label="Scopes"
            value={scopes}
            onChange={(e) => setScopes(e.target.value)}
            helperText="Space or comma separated"
            required
            fullWidth
            multiline
            rows={2}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={loading}>Cancel</Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading}>
          {connectNow ? 'Save & Connect' : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
```

### API Client

**File:** `webui/ui/src/lib/api/credentials.ts`

```typescript
export interface Credential {
  id: string;
  name: string;
  display_name: string;
  provider: string;
  status: string;
  connected_email?: string;
  connected_display_name?: string;
  last_connected_at?: string;
  created_at: string;
}

export interface CreateCredentialRequest {
  display_name: string;
  provider: string;
  client_id: string;
  client_secret: string;
  redirect_uri: string;
  authorization_url: string;
  token_url: string;
  scopes: string[];
}

export async function listCredentials(): Promise<Credential[]> {
  const response = await fetch('/bff/auth/credentials', {
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to list credentials');
  return response.json();
}

export async function createCredential(req: CreateCredentialRequest): Promise<Credential> {
  const response = await fetch('/bff/auth/credentials', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(req)
  });
  if (!response.ok) throw new Error('Failed to create credential');
  return response.json();
}

export async function deleteCredential(credentialId: string): Promise<void> {
  const response = await fetch(`/bff/auth/credentials/${credentialId}`, {
    method: 'DELETE',
    credentials: 'include'
  });
  if (!response.ok) throw new Error('Failed to delete credential');
}

export async function startOAuthFlow(credentialId: string): Promise<string> {
  const response = await fetch(`/bff/auth/oauth/authorize?credential_id=${credentialId}`, {
    credentials: 'include',
    redirect: 'manual'
  });
  
  // Get redirect location from response headers
  const location = response.headers.get('Location');
  if (!location) throw new Error('No OAuth URL returned');
  
  return location;
}
```

### Update BFF Routes

**File:** `webui/bff/src/routes/auth.ts`

```typescript
// Replace /bff/auth/tenants routes with:

// List credentials
router.get('/credentials', verifyJwtMiddleware, async (req: Request, res: Response) => {
  try {
    const response = await fetch('http://auth:8000/auth/credentials', {
      headers: { 'Authorization': `Bearer ${req.jwt}` }
    });
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch credentials' });
  }
});

// Create credential
router.post('/credentials', verifyJwtMiddleware, async (req: Request, res: Response) => {
  try {
    const response = await fetch('http://auth:8000/auth/credentials', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${req.jwt}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(req.body)
    });
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: 'Failed to create credential' });
  }
});

// Delete credential
router.delete('/credentials/:credentialId', verifyJwtMiddleware, async (req: Request, res: Response) => {
  try {
    await fetch(`http://auth:8000/auth/credentials/${req.params.credentialId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${req.jwt}` }
    });
    res.json({ message: 'Deleted' });
  } catch (error) {
    res.status(500).json({ error: 'Failed to delete credential' });
  }
});

// Start OAuth flow
router.get('/oauth/authorize', verifyJwtMiddleware, async (req: Request, res: Response) => {
  try {
    const credentialId = req.query.credential_id as string;
    const response = await fetch(
      `http://auth:8000/auth/oauth/authorize?credential_id=${credentialId}`,
      {
        headers: { 'Authorization': `Bearer ${req.jwt}` },
        redirect: 'manual'
      }
    );
    
    const location = response.headers.get('location');
    if (location) {
      res.redirect(location);
    } else {
      res.status(500).json({ error: 'No OAuth URL returned' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Failed to start OAuth flow' });
  }
});
```

---

## Phase 4: Testing

### Local Testing Checklist

- [ ] Apply migrations (0007, 0008)
- [ ] Start auth service
- [ ] Navigate to `/admin/credentials`
- [ ] Create new credential with Azure app details
- [ ] Click "Save & Connect"
- [ ] Complete OAuth flow
- [ ] Verify credential shows "connected" status
- [ ] Verify tokens stored encrypted in database
- [ ] Test token retrieval via internal endpoint
- [ ] Delete credential and verify cascade delete

---

## Environment Variables Cleanup

### Remove from `.env.local`

```bash
# DELETE these - they move to database:
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_REDIRECT_URI=...
```

### Keep in `.env.local`

```bash
# KEEP these - system-level secrets:
OAUTH_ENCRYPTION_KEY=2QyxEfI726cmiSLpyh1p44YA7ladyom3eGW7LXleyzs=
SERVICE_SECRET=...
JWT_SECRET=...
```

---

## Summary

✅ **Clean slate:** Drop all tenant tables  
✅ **New schema:** `auth.credentials` + `auth.credential_tokens`  
✅ **CRUD endpoints:** Create, read, update, delete credentials  
✅ **OAuth flow:** Dynamic config from database  
✅ **UI components:** Credential management page with form  
✅ **Multiple identifiers:** ID, name, email, external_id  
✅ **Simple validation:** Non-empty fields only  

**Next:** Review this plan, then begin Phase 1 (database migration)
