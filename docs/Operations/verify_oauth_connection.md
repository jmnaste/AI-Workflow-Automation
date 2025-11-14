# Verify OAuth Connection Success

After completing the OAuth flow, verify that the connection was properly established.

## Expected Data in Tables

### 1. `auth.credentials` Table

**Before OAuth (status='pending'):**
```sql
SELECT 
    id, name, display_name, provider, client_id,
    connected_email, external_account_id, connected_display_name,
    status, error_message, last_connected_at,
    created_at, updated_at
FROM auth.credentials
WHERE name = 'your-credential-name';
```

**Expected BEFORE connection:**
- `status` = `'pending'`
- `connected_email` = `NULL`
- `external_account_id` = `NULL`
- `connected_display_name` = `NULL`
- `last_connected_at` = `NULL`
- `error_message` = `NULL`

**Expected AFTER successful connection:**
- `status` = `'connected'`
- `connected_email` = `'user@domain.com'` (the Microsoft/Google account email)
- `external_account_id` = `'<uuid or id>'` (Microsoft user ID or Google sub)
- `connected_display_name` = `'John Doe'` (user's display name from provider)
- `last_connected_at` = `<timestamp>` (when OAuth completed)
- `error_message` = `NULL`

**Expected AFTER failed connection:**
- `status` = `'error'`
- `error_message` = `'<error description>'`
- Other fields remain NULL

---

### 2. `auth.credential_tokens` Table

**Check tokens:**
```sql
SELECT 
    ct.id,
    ct.credential_id,
    c.name as credential_name,
    c.connected_email,
    ct.token_type,
    ct.scopes,
    ct.expires_at,
    ct.created_at,
    ct.last_refreshed_at,
    -- Check if access token is encrypted (should see random characters)
    substring(ct.encrypted_access_token, 1, 50) as access_token_preview,
    -- Check if refresh token exists and is encrypted
    CASE WHEN ct.encrypted_refresh_token IS NOT NULL 
         THEN substring(ct.encrypted_refresh_token, 1, 50) 
         ELSE NULL END as refresh_token_preview,
    -- Check expiry status
    CASE 
        WHEN ct.expires_at < now() THEN 'EXPIRED'
        ELSE 'VALID'
    END as token_status
FROM auth.credential_tokens ct
JOIN auth.credentials c ON ct.credential_id = c.id
WHERE c.name = 'your-credential-name';
```

**Expected AFTER successful connection:**
- One row should exist for the credential
- `token_type` = `'delegated'`
- `encrypted_access_token` = Long encrypted string (e.g., `gAAAAABl...`)
- `encrypted_refresh_token` = Long encrypted string (or NULL if provider doesn't return refresh token)
- `scopes` = Array of scopes (e.g., `{offline_access, https://graph.microsoft.com/Mail.Read}`)
- `expires_at` = Timestamp ~1 hour in future
- `created_at` = When tokens were first stored
- `last_refreshed_at` = NULL (or timestamp if token was refreshed)

**Expected if connection failed:**
- No row in `credential_tokens` table for that credential

---

## Quick Verification Queries

### Check All Credentials Status
```sql
SELECT 
    name,
    display_name,
    provider,
    status,
    connected_email,
    last_connected_at,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM auth.credential_tokens ct 
            WHERE ct.credential_id = c.id 
            AND ct.expires_at > now()
        ) THEN 'HAS_VALID_TOKEN'
        WHEN EXISTS (
            SELECT 1 FROM auth.credential_tokens ct 
            WHERE ct.credential_id = c.id
        ) THEN 'HAS_EXPIRED_TOKEN'
        ELSE 'NO_TOKEN'
    END as token_status
FROM auth.credentials c
ORDER BY created_at DESC;
```

### Check Token Expiry
```sql
SELECT 
    c.name,
    c.connected_email,
    ct.expires_at,
    ct.expires_at - now() as time_until_expiry,
    CASE 
        WHEN ct.expires_at < now() THEN '⚠️ EXPIRED'
        WHEN ct.expires_at < now() + interval '10 minutes' THEN '⏰ EXPIRING SOON'
        ELSE '✅ VALID'
    END as status
FROM auth.credential_tokens ct
JOIN auth.credentials c ON ct.credential_id = c.id
ORDER BY ct.expires_at;
```

### Full Connection Audit
```sql
SELECT 
    c.name,
    c.display_name,
    c.provider,
    c.status,
    c.connected_email,
    c.external_account_id,
    c.last_connected_at,
    ct.expires_at as token_expires_at,
    ct.last_refreshed_at as token_last_refreshed,
    CASE 
        WHEN c.status = 'connected' AND ct.id IS NOT NULL AND ct.expires_at > now() 
        THEN '✅ FULLY CONNECTED'
        WHEN c.status = 'connected' AND ct.id IS NULL 
        THEN '⚠️ MISSING TOKENS'
        WHEN c.status = 'connected' AND ct.expires_at <= now() 
        THEN '⏰ TOKEN EXPIRED'
        WHEN c.status = 'error' 
        THEN '❌ ERROR: ' || c.error_message
        WHEN c.status = 'pending' 
        THEN '⏳ PENDING CONNECTION'
        ELSE '❓ UNKNOWN STATE'
    END as overall_status
FROM auth.credentials c
LEFT JOIN auth.credential_tokens ct ON c.id = ct.credential_id
ORDER BY c.created_at DESC;
```

---

## Running Queries on VPS

### Via Docker Exec
```bash
# Connect to postgres container
docker exec -it postgres psql -U app_root -d app_db

# Then run queries above
```

### Via NetShell (Network Debug Container)
```bash
# Connect to netshell
docker exec -it netshell sh

# Use psql from netshell
psql -h postgres -U app_root -d app_db -c "SELECT name, status, connected_email FROM auth.credentials;"
```

---

## Troubleshooting

### ❌ Credential shows 'pending' after OAuth
**Problem:** OAuth callback didn't execute successfully

**Check:**
1. BFF logs: `docker logs webui --tail 50 | grep -i oauth`
2. Auth logs: `docker logs auth --tail 50 | grep -i oauth`
3. Redirect URI matches Azure/Google configuration exactly
4. Look for error in `error_message` column

### ❌ Credential shows 'error'
**Problem:** OAuth callback failed during processing

**Check:**
```sql
SELECT name, status, error_message, updated_at 
FROM auth.credentials 
WHERE status = 'error';
```

**Common errors:**
- "Invalid client secret" → Wrong client_secret in credential
- "Redirect URI mismatch" → Azure/Google redirect URI doesn't match
- "Invalid grant" → Authorization code expired or already used
- Token encryption error → Missing or wrong `OAUTH_ENCRYPTION_KEY`

### ❌ Credential shows 'connected' but no tokens
**Problem:** Database transaction issue during OAuth callback

**Fix:**
```sql
-- Reset credential to retry OAuth
UPDATE auth.credentials 
SET status = 'pending', 
    connected_email = NULL, 
    external_account_id = NULL,
    error_message = NULL
WHERE id = '<credential-uuid>';

-- Then retry OAuth flow from UI
```

### ✅ Success Indicators
- Credential `status` = `'connected'`
- `connected_email` populated with real email
- `external_account_id` populated
- One row in `credential_tokens` for the credential
- Token `expires_at` is in the future
- Both access and refresh tokens are long encrypted strings

---

## Example Successful Connection

```sql
-- Credential record
auth=# SELECT name, status, connected_email, last_connected_at 
       FROM auth.credentials 
       WHERE name = 'acme-ms365';
       
    name     |  status   |     connected_email      |   last_connected_at    
-------------+-----------+--------------------------+------------------------
 acme-ms365  | connected | john@acme.onmicrosoft.com| 2025-11-14 15:30:42+00
(1 row)

-- Token record
auth=# SELECT credential_id, expires_at, 
              substring(encrypted_access_token, 1, 30) as token_preview
       FROM auth.credential_tokens ct
       JOIN auth.credentials c ON ct.credential_id = c.id
       WHERE c.name = 'acme-ms365';
       
           credential_id            |      expires_at         |       token_preview        
------------------------------------+-------------------------+----------------------------
 a1b2c3d4-5678-90ab-cdef-1234567890 | 2025-11-14 16:30:42+00 | gAAAAABl1K2x3N4p5Q6r7S8t9U...
(1 row)
```

This indicates OAuth connection was **fully successful**.
