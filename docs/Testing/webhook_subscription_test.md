# Test 4: Create MS365 Webhook Subscription

**Date**: 2025-11-15  
**Status**: Ready to Execute  
**Prerequisites**: Tests 1-3 completed (services healthy, credential connected, message fetching works)

---

## Overview

This test creates an MS365 webhook subscription that will notify our API whenever new emails arrive in the inbox.

**What happens**:
1. We call `/api/ms365/subscriptions` with subscription details
2. API calls Microsoft Graph API to create subscription
3. MS365 sends validation challenge to our webhook endpoint
4. Our endpoint must respond with the validation token
5. MS365 activates the subscription
6. Subscription details stored in `api.webhook_subscriptions` table

---

## Prerequisites Configuration

### **Step 1: Configure Public Webhook Endpoint**

MS365 requires the webhook endpoint to be **publicly accessible via HTTPS**.

**In Hostinger → API Project → Environment, add:**

```bash
API_PUBLIC=true
API_WEBHOOK_HOST=webhooks.flovify.ca
API_WEBHOOK_PATH_PREFIX=/webhooks
API_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=mytlschallenge
```

**Then restart API service.**

### **Step 2: Verify DNS**

Ensure DNS A record exists:
```
webhooks.flovify.ca → <Your VPS IP>
```

### **Step 3: Verify Traefik**

Traefik should be running with Let's Encrypt configured for automatic TLS certificates.

---

## Test Commands

### **From NetShell Container**

```bash
# Enter netshell (if not already in it)
docker exec -it netshell sh
```

### **1. Test Internal Validation Endpoint**

```bash
curl "http://api:8000/webhooks/ms365/webhook?validationToken=test123"
```

**Expected Response:**
```
test123
```

**Status**: 200 OK, plain text

---

### **2. Test Public Validation Endpoint** (Optional)

From your local machine (Windows PowerShell):

```powershell
curl https://webhooks.flovify.ca/webhooks/ms365/webhook?validationToken=test456
```

**Expected Response:**
```
test456
```

**Status**: 200 OK with valid TLS certificate

---

### **3. Create Webhook Subscription**

**From NetShell:**

```bash
# Set your credential ID
CREDENTIAL_ID="37b08f02-62d8-4327-aac7-f20e13b7f440"

# Create subscription
curl -X POST http://api:8000/webhooks/ms365/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "credential_id": "'"$CREDENTIAL_ID"'",
    "resource": "me/mailFolders('\''inbox'\'')/messages",
    "change_types": ["created"],
    "notification_url": "https://webhooks.flovify.ca/webhooks/ms365/webhook",
    "expiration_hours": 72
  }'
```

**Expected Success Response:**

```json
{
  "id": "uuid-of-subscription",
  "credential_id": "37b08f02-62d8-4327-aac7-f20e13b7f440",
  "provider": "ms365",
  "external_subscription_id": "ms365-subscription-id",
  "resource_path": "me/mailFolders('inbox')/messages",
  "notification_url": "https://webhooks.flovify.ca/webhooks/ms365/webhook",
  "change_types": ["created"],
  "status": "active",
  "expires_at": "2025-11-18T...",
  "created_at": "2025-11-15T...",
  "last_notification_at": null
}
```

**Status**: 201 Created

---

### **4. Verify in Database**

```bash
psql -h postgres -U app_root -d app_db -c "
  SELECT 
    id, 
    credential_id, 
    status, 
    resource_path, 
    expires_at 
  FROM api.webhook_subscriptions 
  ORDER BY created_at DESC 
  LIMIT 1;
"
```

**Expected**: One row with `status='active'` and future `expires_at` timestamp

---

## Common Issues

### **Issue 1: Subscription Creation Fails with "Validation failed"**

**Cause**: MS365 cannot reach public webhook endpoint

**Solutions**:
- Verify `API_PUBLIC=true` is set and API service restarted
- Check DNS: `nslookup webhooks.flovify.ca` (should resolve to VPS IP)
- Test public endpoint manually (Step 2 above)
- Check Traefik logs: `docker logs traefik | grep webhooks`
- Verify firewall allows HTTPS (port 443) inbound

### **Issue 2: Response "Invalid notification_url"**

**Cause**: URL must be HTTPS, not HTTP

**Solution**: Ensure `notification_url` starts with `https://`

### **Issue 3: Response "credential not found or not connected"**

**Cause**: Credential ID is wrong or credential not connected

**Solutions**:
- Verify credential ID: Use the one from Test 2 (credential validation)
- Check credential status: `psql -h postgres -U app_root -d app_db -c "SELECT id, provider, is_connected FROM auth.credentials;"`
- Reconnect credential if needed via Admin UI

### **Issue 4: 500 Internal Server Error**

**Cause**: API service error

**Solutions**:
- Check API logs: `docker logs api --tail 50`
- Verify `SERVICE_SECRET` matches between Auth and API
- Check Auth service is running: `curl http://auth:8000/auth/health`

---

## Success Criteria

✅ Internal validation endpoint returns token  
✅ Public validation endpoint returns token with valid TLS  
✅ Subscription created successfully (201 response)  
✅ Database has active subscription record  
✅ `external_subscription_id` populated (MS365 accepted subscription)  
✅ `expires_at` is ~72 hours in future  

---

## Next Steps

After successful subscription creation:

**Test 5**: Trigger webhook notification by sending test email  
**Test 6**: Verify worker processes the event  
**Test 7**: Test subscription management (list, renew, delete)  
**Test 8**: Test error handling (retries)

---

## Reference

- **MS365 Subscription API**: https://learn.microsoft.com/en-us/graph/api/subscription-post-subscriptions
- **Webhook Validation**: https://learn.microsoft.com/en-us/graph/webhooks#notification-endpoint-validation
- **Subscription Expiration**: Mail subscriptions max 4230 hours (~176 days)
