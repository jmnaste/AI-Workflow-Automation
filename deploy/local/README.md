# Local Testing Guide

This directory contains configuration for running the entire stack locally with Docker Compose.

## Quick Start

### 1. Setup Environment Variables

```powershell
# Copy template and fill in your values
cd deploy/local
copy .env.local.template .env.local
# Edit .env.local with your credentials
```

**Required variables to fill in `.env.local`:**
- `JWT_SECRET` - Generate with: `openssl rand -base64 32`
- Either `TWILIO_*` (for SMS) or `SMTP_*` (for Email) credentials

### 2. Create Traefik Network

```powershell
docker network create root_default
```

### 3. Start the Stack

```powershell
cd deploy/local
docker-compose -f docker-compose.local.yml up --build
```

**Services started:**
- PostgreSQL on `localhost:5432` (internal DNS: `postgres:5432`)
- Auth Service on `localhost:8000` (internal DNS: `auth:8000`)
- API Service on `localhost:8001` (internal DNS: `api:8000`)
- WebUI on `localhost:80` (internal DNS: `webui:80`)

### 4. Access the Application

Open your browser: **http://localhost**

## Common Commands

### View Logs

```powershell
# All services
docker-compose -f docker-compose.local.yml logs -f

# Specific service
docker-compose -f docker-compose.local.yml logs -f auth
docker-compose -f docker-compose.local.yml logs -f api
docker-compose -f docker-compose.local.yml logs -f webui
docker-compose -f docker-compose.local.yml logs -f postgres
```

### Rebuild Single Service

```powershell
# Fast iteration - rebuild only changed service
docker-compose -f docker-compose.local.yml up --build auth
docker-compose -f docker-compose.local.yml up --build api
docker-compose -f docker-compose.local.yml up --build webui
```

### Stop Stack

```powershell
# Stop but keep data
docker-compose -f docker-compose.local.yml down

# Stop and remove volumes (fresh start)
docker-compose -f docker-compose.local.yml down -v
```

### Check Service Health

```powershell
# Auth Service health check
curl http://localhost:8000/auth/health
curl http://localhost:8000/auth/db/health

# API Service health check
curl http://localhost:8001/api/health
curl http://localhost:8001/api/db/health

# PostgreSQL connection test
docker exec -it postgres psql -U flovify -d flovify -c "\dt auth.*"
```

## Testing Authentication Flow

### 1. Request OTP via API

```powershell
# New user (requires phone and preference)
curl -X POST http://localhost/bff/auth/request-otp `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","phone":"+15551234567","preference":"email"}'

# Existing user (uses saved preference)
curl -X POST http://localhost/bff/auth/request-otp `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com"}'
```

### 2. Check Email/SMS for OTP Code

Look for 6-digit code in your email inbox or SMS.

### 3. Verify OTP

```powershell
curl -X POST http://localhost/bff/auth/verify-otp `
  -H "Content-Type: application/json" `
  -d '{"email":"test@example.com","otp":"123456"}' `
  --cookie-jar cookies.txt
```

### 4. Get Current User

```powershell
curl http://localhost/bff/auth/me --cookie cookies.txt
```

### 5. Logout

```powershell
curl -X POST http://localhost/bff/auth/logout --cookie cookies.txt
```

## Troubleshooting

### Services won't start

1. **Check network exists:**
   ```powershell
   docker network ls | findstr root_default
   ```

2. **Check ports not in use:**
   ```powershell
   netstat -ano | findstr ":80 "
   netstat -ano | findstr ":5432 "
   netstat -ano | findstr ":8000 "
   netstat -ano | findstr ":8001 "
   ```

3. **Check environment variables:**
   ```powershell
   # Ensure .env.local exists and has values
   cat .env.local
   ```

### Database connection failed

1. **Check PostgreSQL is running:**
   ```powershell
   docker-compose -f docker-compose.local.yml ps postgres
   ```

2. **Check database logs:**
   ```powershell
   docker-compose -f docker-compose.local.yml logs postgres
   ```

3. **Test connection:**
   ```powershell
   docker exec -it postgres psql -U flovify -d flovify -c "SELECT 1"
   ```

### OTP not sending

1. **For Email (SMTP):**
   - Verify SMTP credentials in `.env.local`
   - Check Gmail app password is correct
   - Check Auth Service logs: `docker-compose -f docker-compose.local.yml logs auth`

2. **For SMS (Twilio):**
   - Verify Twilio credentials in `.env.local`
   - Check Twilio account has credits
   - Check phone number includes country code (+1...)

### JWT errors

- Ensure `JWT_SECRET` is identical in Auth Service and BFF
- Check it's at least 32 characters long

## Architecture

```
Browser (localhost)
    ↓
WebUI (Nginx) :80
    ↓ /bff/* → BFF (Express) :3001
    ↓
    ├─→ Auth Service :8000 → PostgreSQL :5432
    └─→ API Service :8001 → PostgreSQL :5432

All containers on "root_default" Docker network
```

## Environment Variables

See `.env.local.template` for full list of configurable variables.

**Key variables:**
- `JWT_SECRET` - Must match between Auth and BFF
- `POSTGRES_PASSWORD` - Database password
- `TWILIO_*` or `SMTP_*` - OTP delivery method
- `OTP_*` - OTP expiration and rate limiting config

## VPS Parity

Local setup mirrors VPS deployment:
- ✅ Same Docker network (`root_default`)
- ✅ Same service structure and labels
- ✅ Same environment variable names
- ✅ Builds from source (local) vs pulls from GHCR (VPS)
- ✅ Exposed ports for debugging (local) vs Traefik routing (VPS)

**Differences from VPS:**
- Local: Direct port access (`:80`, `:8000`, `:8001`, `:5432`)
- VPS: Traefik routing with TLS (`:443` with Let's Encrypt)

## Next Steps

After successful local testing:
1. Commit changes (excluding `.env.local`)
2. Push to GitHub (triggers GHCR image builds)
3. Deploy to VPS with VPS-specific compose files
4. Use same environment variable names in Hostinger UI
