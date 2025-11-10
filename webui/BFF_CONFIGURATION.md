# WebUI BFF Configuration Reference

This document explains all configuration settings for the WebUI Backend for Frontend (BFF) service.

## Architecture Overview

**BFF Role**: Thin proxy layer between UI and backend services (Auth and API).

- **Does NOT** access database directly
- **Does NOT** contain business logic
- Routes requests to appropriate services (Auth for authentication, API for business data)
- Manages JWT httpOnly cookies (receives from Auth Service, sets in browser)

## Environment Variables

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NODE_ENV` | No | `development` | Runtime environment (`development`, `production`) |
| `PORT` | No | `3001` | BFF server port |
| `LOG_LEVEL` | No | `info` | Logging level (`debug`, `info`, `warn`, `error`) |
| `CORS_ORIGIN` | No | `http://localhost:5173` | Allowed CORS origin for development |

### Backend Service URLs

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_BASE_URL` | No | `http://auth:8000` | Auth service URL (Docker DNS) |
| `API_BASE_URL` | No | `http://api:8000` | API service URL (Docker DNS) |

### JWT Authentication (Cookie Management Only)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | **Yes** | - | Secret key for verifying JWT tokens (must match Auth Service) |
| `JWT_COOKIE_NAME` | No | `flovify_token` | Name of httpOnly cookie storing JWT |

**Note**: BFF only **verifies** JWTs (for extracting user info before proxying). The Auth Service **generates** JWTs.

**Generate secure secret** (use same value in Auth Service):
```bash
openssl rand -base64 32
OTP_EXPIRY_MINUTES=5
OTP_MAX_ATTEMPTS=5
RATE_LIMIT_WINDOW_MINUTES=1
RATE_LIMIT_MAX_REQUESTS=10
```

---

## Authentication Flow (BFF as Proxy)

### How OTP Authentication Works

1. **User Requests OTP**
   - User enters email on sign-in page
   - Frontend calls `POST /bff/auth/request-otp`
   - **BFF proxies to Auth Service**: `POST http://auth:8000/auth/request-otp`
   - Auth Service handles rate limiting, OTP generation, and delivery

2. **Auth Service Generates OTP**
   - Auth Service generates random 6-digit code
   - Code is hashed with bcrypt before storage in PostgreSQL
   - Stored with 5-minute expiration

3. **Auth Service Sends OTP**
   - Delivers OTP via SMS (Twilio) or Email (SMTP) based on user preference
   - Returns success to BFF
   - BFF returns success to UI

4. **User Submits OTP**
   - User enters 6-digit code on sign-in page
   - Frontend calls `POST /bff/auth/verify-otp`
   - **BFF proxies to Auth Service**: `POST http://auth:8000/auth/verify-otp`

5. **Auth Service Validates OTP**
   - Checks OTP hash, expiration, and attempt count in PostgreSQL
   - Generates JWT with user claims (userId, email)
   - Returns JWT and user profile to BFF

6. **BFF Sets Cookie**
   - BFF receives JWT from Auth Service
   - Sets JWT in httpOnly, secure, sameSite cookie
   - Returns user profile to UI
   - User is now authenticated

### Protected Requests

1. **UI makes authenticated request**
   - Request includes httpOnly cookie with JWT
   - `GET /bff/auth/me` or `GET /bff/api/workflows`

2. **BFF extracts and validates JWT**
   - Reads JWT from cookie
   - Verifies signature using JWT_SECRET
   - Extracts user info (userId, email)

3. **BFF proxies to backend**
   - Adds user info to request headers or body
   - Forwards to Auth Service or API Service
   - Returns response to UI

---

## Configuration in Auth Service

The following configuration is managed by the **Auth Service** (not BFF):

### OTP Configuration (in Auth Service)
- `OTP_EXPIRY_MINUTES` - OTP expiration time
- `OTP_MAX_ATTEMPTS` - Max validation attempts
- `RATE_LIMIT_WINDOW_MINUTES` - Rate limit time window
- `RATE_LIMIT_MAX_REQUESTS` - Max OTP requests per window

### Twilio SMS (in Auth Service)
- `TWILIO_ACCOUNT_SID` - Twilio account SID
- `TWILIO_AUTH_TOKEN` - Twilio auth token
- `TWILIO_PHONE_NUMBER` - Twilio phone number

### SMTP Email (in Auth Service)
- `SMTP_HOST` - SMTP server hostname
- `SMTP_PORT` - SMTP port (587 for TLS, 465 for SSL)
- `SMTP_USER` - SMTP username
- `SMTP_PASS` - SMTP password or app password
- `SMTP_FROM` - From email address

### PostgreSQL (in Auth Service)
- `POSTGRES_HOST` - Database hostname
- `POSTGRES_PORT` - Database port
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database username
- `POSTGRES_PASSWORD` - Database password

**See Auth Service documentation** for detailed configuration of OTP, SMS, Email, and database settings
   - User submits code via `POST /bff/auth/verify-otp`
   - BFF checks if code exists and hasn't expired
   - Validates against hashed version (secure comparison)
   - Tracks validation attempts (max 3)

7. **Success**
   - If valid: Issue JWT token, set httpOnly cookie, return user profile
   - If invalid: Return error, increment attempt counter
   - If expired or max attempts: Delete OTP, user must request new one

### Email Template Structure

```html
<div class="container">
---

## Complete Example Configuration

### Development (Local)

```env
# Core
NODE_ENV=development
PORT=3001
LOG_LEVEL=debug
CORS_ORIGIN=http://localhost:5173

# Backend Services (Docker DNS names)
AUTH_BASE_URL=http://auth:8000
API_BASE_URL=http://api:8000

# JWT (must match Auth Service secret)
JWT_SECRET=dev_secret_change_in_production_at_least_32_chars
JWT_COOKIE_NAME=flovify_token
```

### Production (VPS)

```env
# Core
NODE_ENV=production
PORT=3001
LOG_LEVEL=info
CORS_ORIGIN=https://console.flovify.ca

# Backend Services (Docker network)
AUTH_BASE_URL=http://auth:8000
API_BASE_URL=http://api:8000

# JWT (must match Auth Service secret)
JWT_SECRET=<use-openssl-rand-base64-32>
JWT_COOKIE_NAME=flovify_token

# Database (Docker network)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=flovify
POSTGRES_USER=flovify
POSTGRES_PASSWORD=<strong-generated-password>

# JWT
JWT_SECRET=<openssl-rand-base64-32-output>
JWT_COOKIE_NAME=flovify_token

# OTP (strict)
OTP_EXPIRY_MINUTES=5
OTP_MAX_ATTEMPTS=3
RATE_LIMIT_WINDOW_MINUTES=15
RATE_LIMIT_MAX_REQUESTS=3

# Twilio
TWILIO_ACCOUNT_SID=<your-twilio-account-sid>
TWILIO_AUTH_TOKEN=<your-twilio-auth-token>
TWILIO_PHONE_NUMBER=+1234567890

# SMTP (SendGrid or production email service)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=<your-sendgrid-api-key>
SMTP_FROM=noreply@flovify.ca
```

---

## Troubleshooting

### Auth requests failing

1. **Check Auth Service is running**: `docker ps | grep auth`
2. **Verify AUTH_BASE_URL**: Should be `http://auth:8000` (Docker DNS)
3. **Check network**: BFF and Auth must be on same Docker network
4. **Check Auth logs**: `docker logs auth`
5. **Test Auth directly**: `curl http://auth:8000/auth/health`

### JWT cookie not being set

1. **Verify JWT_SECRET matches Auth Service**: Both must use same secret
2. **Check cookie domain/path**: Should work for your domain
3. **HTTPS required in production**: Secure flag requires HTTPS
4. **Browser dev tools**: Check Application → Cookies for `flovify_token`

### "Unauthorized" errors

1. **Check JWT_SECRET**: Must match between BFF and Auth Service
2. **Cookie expired**: JWT expires after 7 days
3. **Cookie not sent**: Check browser is sending cookie with requests
4. **Invalid token**: User may need to log in again

---

## Auth Service Configuration

For OTP, SMS, Email, Database, and Rate Limiting configuration, see the **Auth Service documentation**.

BFF only needs to know:
- `AUTH_BASE_URL` - Where to proxy auth requests
- `JWT_SECRET` - How to verify tokens (must match Auth Service)
