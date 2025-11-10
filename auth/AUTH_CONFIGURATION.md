# Auth Service Configuration

This document explains the configuration for the Auth Service (OTP-based authentication).

## Environment Variables

### Database Connection (Required)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | - | PostgreSQL connection string (e.g., `postgresql://user:pass@postgres:5432/dbname`) |

### JWT Configuration (Required)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | **Yes** | - | Secret key for signing JWT tokens (min 32 chars, use `openssl rand -base64 32`) |

### OTP Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OTP_EXPIRY_MINUTES` | No | `5` | OTP expiration time in minutes |
| `OTP_MAX_ATTEMPTS` | No | `3` | Maximum validation attempts per OTP |
| `RATE_LIMIT_WINDOW_MINUTES` | No | `15` | Rate limit time window in minutes |
| `RATE_LIMIT_MAX_REQUESTS` | No | `3` | Max OTP requests per window per email |

**Development Settings** (for faster testing):
```env
OTP_EXPIRY_MINUTES=10
OTP_MAX_ATTEMPTS=5
RATE_LIMIT_WINDOW_MINUTES=1
RATE_LIMIT_MAX_REQUESTS=10
```

### Twilio SMS Configuration (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TWILIO_ACCOUNT_SID` | Yes (for SMS) | - | Twilio account SID from console |
| `TWILIO_AUTH_TOKEN` | Yes (for SMS) | - | Twilio auth token from console |
| `TWILIO_PHONE_NUMBER` | Yes (for SMS) | - | Twilio phone number with country code (e.g., +1234567890) |

**Note**: Either Twilio OR SMTP must be configured. Users choose their preferred delivery method.

### SMTP Email Configuration (Optional)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SMTP_HOST` | Yes (for email) | - | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP port (587 for TLS, 465 for SSL) |
| `SMTP_USER` | Yes (for email) | - | SMTP username/email |
| `SMTP_PASS` | Yes (for email) | - | SMTP password or app-specific password |
| `SMTP_FROM` | No | `noreply@flovify.ca` | From email address for OTP emails |

**Common SMTP Providers**:

**Gmail**:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-specific-password
```
(Generate app password: https://myaccount.google.com/apppasswords)

**Outlook/Office365**:
```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@outlook.com
SMTP_PASS=your-password
```

**SendGrid**:
```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=your-sendgrid-api-key
```

**Mailgun**:
```env
SMTP_HOST=smtp.mailgun.org
SMTP_PORT=587
SMTP_USER=postmaster@your-domain.mailgun.org
SMTP_PASS=your-mailgun-smtp-password
```

---

## API Endpoints

### POST /auth/request-otp

Request OTP for email authentication.

**Request Body**:
```json
{
  "email": "user@example.com",
  "phone": "+1234567890",     // Required for new users
  "preference": "sms"          // Required for new users: "sms" or "email"
}
```

**Response**:
```json
{
  "success": true,
  "message": "OTP sent to your sms",
  "isNewUser": false
}
```

### POST /auth/verify-otp

Verify OTP and receive JWT token.

**Request Body**:
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```

**Response**:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "phone": "+1234567890",
    "otpPreference": "sms",
    "createdAt": "2025-11-09T12:00:00Z",
    "lastLoginAt": "2025-11-09T12:00:00Z"
  }
}
```

### GET /auth/me

Get current user profile (requires Authorization header).

**Headers**:
```
Authorization: Bearer <jwt-token>
```

**Response**:
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "phone": "+1234567890",
  "otpPreference": "sms",
  "createdAt": "2025-11-09T12:00:00Z",
  "lastLoginAt": "2025-11-09T12:00:00Z"
}
```

### POST /auth/logout

Logout (client clears cookie/token).

**Response**:
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## Database Schema

The Auth Service creates the following tables in the `auth` schema:

### auth.users

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() |
| `email` | VARCHAR(255) | UNIQUE NOT NULL, CHECK (lowercase) |
| `phone` | VARCHAR(50) | - |
| `otp_preference` | VARCHAR(10) | CHECK IN ('sms', 'email') |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() |
| `last_login_at` | TIMESTAMPTZ | - |

**Indexes**: `email`, `created_at DESC`

### auth.otp_storage

| Column | Type | Constraints |
|--------|------|-------------|
| `email` | VARCHAR(255) | PRIMARY KEY |
| `otp_hash` | VARCHAR(255) | NOT NULL (bcrypt hash) |
| `attempts` | INTEGER | DEFAULT 0 |
| `expires_at` | TIMESTAMPTZ | NOT NULL |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() |

### auth.rate_limit

| Column | Type | Constraints |
|--------|------|-------------|
| `email` | VARCHAR(255) | PRIMARY KEY |
| `request_count` | INTEGER | DEFAULT 0 |
| `window_start` | TIMESTAMPTZ | NOT NULL |

---

## Complete Example Configuration

### Development

```env
# Database
DATABASE_URL=postgresql://flovify:dev_password@localhost:5432/flovify

# JWT
JWT_SECRET=dev_secret_change_in_production_at_least_32_chars

# OTP (relaxed for testing)
OTP_EXPIRY_MINUTES=10
OTP_MAX_ATTEMPTS=5
RATE_LIMIT_WINDOW_MINUTES=1
RATE_LIMIT_MAX_REQUESTS=10

# SMTP (Gmail for dev)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=dev@flovify.ca
SMTP_PASS=your-gmail-app-password
SMTP_FROM=noreply@flovify.ca
```

### Production

```env
# Database
DATABASE_URL=postgresql://flovify:strong_password@postgres:5432/flovify

# JWT
JWT_SECRET=<use-openssl-rand-base64-32>

# OTP (production defaults)
OTP_EXPIRY_MINUTES=5
OTP_MAX_ATTEMPTS=3
RATE_LIMIT_WINDOW_MINUTES=15
RATE_LIMIT_MAX_REQUESTS=3

# Twilio SMS
TWILIO_ACCOUNT_SID=<your-twilio-sid>
TWILIO_AUTH_TOKEN=<your-twilio-token>
TWILIO_PHONE_NUMBER=+1234567890

# SMTP (SendGrid for production)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=<your-sendgrid-api-key>
SMTP_FROM=noreply@flovify.ca
```

---

## Security Features

1. **Bcrypt OTP Hashing**: OTPs are hashed with bcrypt before storage
2. **Expiration**: Codes automatically expire after configured time
3. **Rate Limiting**: Prevents brute force attacks
4. **Attempt Limiting**: Max attempts per OTP code
5. **JWT Tokens**: 7-day expiry, signed with HS256
6. **Database Constraints**: Email uniqueness, lowercase enforcement

---

## Troubleshooting

### Database connection failed

```bash
# Check DATABASE_URL format
postgresql://user:password@host:port/database

# Test connection
psql "postgresql://user:password@host:port/database"
```

### SMS not sending

1. Verify Twilio credentials in console
2. Check phone number format includes country code (+1...)
3. Ensure Twilio account has credits
4. Check logs: `docker logs auth`

### Email not sending

1. Check SMTP credentials
2. Verify SMTP_HOST and SMTP_PORT
3. Try test email with credentials
4. Check firewall allows outbound port 587
5. Check logs: `docker logs auth`

### Rate limit too restrictive

```env
RATE_LIMIT_WINDOW_MINUTES=1
RATE_LIMIT_MAX_REQUESTS=10
```

### JWT verification fails

Ensure JWT_SECRET matches between Auth Service and BFF.
