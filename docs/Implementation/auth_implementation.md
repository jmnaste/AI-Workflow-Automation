# Authentication Implementation - OTP-based Passwordless Login

## Architecture Decision (Updated 2025-11-09)

**Service Responsibilities:**
- **Auth Service (Python/FastAPI)**: Owns authentication logic and user identity
  - OTP generation, validation, storage
  - User table management (email, phone, preferences)
  - JWT token generation
  - SMS/Email delivery integration
  - Direct PostgreSQL access for auth tables
- **BFF (Node.js/Express)**: Thin proxy layer only
  - Routes UI requests to Auth Service
  - Manages JWT httpOnly cookies (receives from Auth, sets in browser)
  - **No business logic**
  - **No database access**

## Overview
Implement passwordless authentication using OTP (One-Time Password) delivered via SMS (Twilio) or Email.

## User Flow
1. User enters email (UI → BFF → Auth Service)
2. Auth Service checks if user exists:
   - **New user**: Collect phone number and OTP delivery preference (SMS/Email)
   - **Existing user**: Use saved preference
3. Auth Service generates and sends 6-digit OTP via SMS/Email
4. User enters OTP (UI → BFF → Auth Service)
5. Auth Service validates OTP, generates JWT, returns to BFF
6. BFF sets JWT in httpOnly cookie, returns success to UI

---

## Phase 1: UI Implementation ✅ COMPLETED

### Components
- [x] Multi-step SignIn form component
  - [x] Step 1: Email entry
  - [x] Step 2: Phone number + preference (new users only)
  - [x] Step 3: OTP entry
- [x] Form validation with Zod schemas
- [x] Loading and error states
- [x] Success feedback

### API Client
- [x] Create `ui/src/lib/api/auth.ts` with functions:
  - [x] `requestOtp(email, phone?, preference?)`
  - [x] `verifyOtp(email, otp)`
  - [x] `getCurrentUser()`
- [x] Mock responses for initial testing

### Auth State Management
- [x] Update `ui/src/lib/auth.ts` with:
  - [x] Store user profile in session
  - [x] Handle JWT cookie (httpOnly, handled by BFF)
  - [x] isAuthenticated check
  - [x] Logout function

### Routing
- [x] Update protected routes to check auth state
- [x] Redirect to /sign-in if not authenticated
- [x] Redirect to /dashboard after successful login
- [x] Initialize auth on app load
- [x] Update AppLayout to use real auth state

---

## Phase 2: Auth Service Implementation (Python/FastAPI) ✅ COMPLETED

### Dependencies (in auth service)
- [x] Install libraries in `auth/requirements.txt`:
  - [x] `twilio` - SMS delivery
  - [x] `psycopg[binary]` - PostgreSQL client (already installed)
  - [x] `bcrypt` - OTP hashing
  - [x] `pyjwt` - JWT generation
  - [x] `python-multipart` - Form data handling
  - [x] `pydantic-settings` - Environment config

### Database Schema (PostgreSQL)
- [x] Create users table in auth schema:
  - [x] `id` (UUID, primary key)
  - [x] `email` (VARCHAR, unique, lowercase)
  - [x] `phone` (VARCHAR)
  - [x] `otp_preference` (VARCHAR: 'sms' or 'email')
  - [x] `created_at`, `last_login_at` (TIMESTAMPTZ)
- [x] Create otp_storage table:
  - [x] `email` (VARCHAR, primary key)
  - [x] `otp_hash` (VARCHAR, bcrypt hash)
  - [x] `attempts` (INTEGER)
  - [x] `expires_at` (TIMESTAMPTZ)
  - [x] `created_at` (TIMESTAMPTZ)
- [x] Create rate_limit table:
  - [x] `email` (VARCHAR, primary key)
  - [x] `request_count` (INTEGER)
  - [x] `window_start` (TIMESTAMPTZ)

### OTP Management
- [x] Create `auth/app/services/otp.py`
  - [x] Generate 6-digit OTP
  - [x] Store OTP hash with expiry (5min TTL)
  - [x] Validate OTP with bcrypt
  - [x] Rate limiting (configurable, default 3 requests per 15min)
  - [x] Max attempts tracking (3 attempts per OTP)
  - [x] Automatic cleanup of expired OTPs

### Twilio Integration
- [x] Create `auth/app/services/sms.py`
  - [x] Initialize Twilio client
  - [x] Send SMS function with formatted message
  - [x] Error handling and configuration check

### Email Integration
- [x] Create `auth/app/services/email.py`
  - [x] Configure SMTP client
  - [x] Send OTP email function
  - [x] HTML email template with branding
  - [x] Plain text fallback

### User Management
- [x] Create `auth/app/services/users.py`
  - [x] PostgreSQL CRUD operations
  - [x] findByEmail, create, update, delete
  - [x] Store: id, email, phone, otp_preference, timestamps

### Auth Endpoints (FastAPI)
- [x] Update `auth/app/main.py` with routes:
  - [x] `POST /auth/request-otp`
    - [x] Validate email with Pydantic
    - [x] Check if user exists in database
    - [x] If new: require phone + preference
    - [x] Rate limiting check
    - [x] Generate and store OTP hash
    - [x] Send via SMS or Email
    - [x] Return success with isNewUser flag
  - [x] `POST /auth/verify-otp`
    - [x] Validate OTP with Pydantic
    - [x] Check expiry and attempts in database
    - [x] Generate JWT with PyJWT
    - [x] Update last login timestamp
    - [x] Return JWT and user profile
  - [x] `GET /auth/me`
    - [x] Validate JWT from Authorization header
    - [x] Return user profile from database
  - [x] `POST /auth/logout`
    - [x] Return success (client clears cookie)

### JWT Implementation
- [x] Create `auth/app/services/jwt.py`
  - [x] Sign JWT with user claims (userId, email)
  - [x] Verify JWT function
  - [x] 7-day expiry
  - [x] Use JWT_SECRET from environment

### Environment Variables
- [x] Add to `auth/auth.compose.yml`:
  - [x] PostgreSQL connection (DATABASE_URL)
  - [x] JWT secret (JWT_SECRET)
  - [x] Twilio credentials (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)
  - [x] SMTP config (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM)
  - [x] OTP config (OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS)
  - [x] Rate limiting (RATE_LIMIT_WINDOW_MINUTES, RATE_LIMIT_MAX_REQUESTS)

### Documentation
- [x] Create `auth/AUTH_CONFIGURATION.md` with complete configuration guide

---

## Phase 2B: BFF Simplification (Proxy Layer Only) ✅ COMPLETED

### Remove Direct Database Access
- [x] Delete `bff/src/services/database.ts`
- [x] Delete `bff/src/services/users.ts`
- [x] Delete `bff/src/services/otp.ts`
- [x] Delete `bff/src/services/sms.ts`
- [x] Delete `bff/src/services/email.ts`
- [x] Remove `pg` dependency from `bff/package.json`
- [x] Remove `twilio` and `nodemailer` dependencies

### Proxy Implementation
- [x] Update `bff/src/routes/auth.ts` to proxy to Auth Service:
  - [x] `POST /bff/auth/request-otp` → `POST http://auth:8000/auth/request-otp`
  - [x] `POST /bff/auth/verify-otp` → `POST http://auth:8000/auth/verify-otp`
    - [x] Receive JWT from Auth Service
    - [x] Set JWT in httpOnly cookie (using existing jwt.ts utilities)
    - [x] Return user profile to UI
  - [x] `GET /bff/auth/me` → validate JWT from cookie, proxy to Auth Service
  - [x] `POST /bff/auth/logout` → clear cookie, return success

### Keep JWT Cookie Management
- [x] Keep `bff/src/middleware/jwt.ts` (for cookie operations only)
  - [x] Keep: setAuthCookie, clearAuthCookie
  - [x] Keep: verifyToken (for extracting user from cookie before proxying)
  - [x] Remove: signToken (Auth Service generates JWTs now)

### Environment Variables
- [x] Update `webui/webui.compose.yml`:
  - [x] Remove PostgreSQL variables (no longer needed by BFF)
  - [x] Remove Twilio/SMTP variables (Auth Service owns these)
  - [x] Remove OTP config variables (Auth Service owns these)
  - [x] Keep: AUTH_BASE_URL (points to auth:8000)
  - [x] Keep: JWT_SECRET (for cookie verification, must match Auth Service)

### Documentation Updates
- [x] Update `webui/README.md` to reflect BFF as proxy layer
- [x] Update `webui/BFF_CONFIGURATION.md` (already done in previous task)

---

## Phase 3: Testing & Refinement

### Local Testing
- [ ] Test email OTP flow
- [ ] Test SMS OTP flow (with Twilio test credentials)
- [ ] Test new user registration
- [ ] Test existing user login
- [ ] Test invalid OTP
- [ ] Test expired OTP
- [ ] Test rate limiting

### Security Hardening
- [ ] Rate limit OTP requests (max 3 per 15min per email)
- [ ] Hash OTPs before storing
- [ ] Validate phone number format
- [ ] Add CSRF protection
- [ ] Secure JWT secret rotation plan

### UI/UX Polish
- [ ] Add "Resend OTP" button with countdown
- [ ] Show clear error messages
- [ ] Add loading spinners
- [ ] Mobile responsive design
- [ ] Accessibility (ARIA labels, keyboard nav)

### Documentation
- [ ] Update README with auth flow
- [ ] Document environment variables
- [ ] Add troubleshooting guide
- [ ] Update DESIGN_SYSTEM.md with auth UI patterns

---

## Future Enhancements (Phase 4+)
- [ ] Move OTP storage to Redis for multi-instance support
- [ ] Add "Remember me" option (longer JWT expiry)
- [ ] Add user profile management page
- [ ] Add OAuth2 providers (Google, GitHub)
- [ ] Add 2FA for sensitive operations
- [ ] Add audit log for auth events
- [ ] Add email verification for new accounts
- [ ] Add account recovery flow

---

## Current Status
**Phase:** 1 (UI Implementation) - ✅ COMPLETED  
**Phase:** 2A (Auth Service Implementation) - ✅ COMPLETED  
**Phase:** 2B (BFF Simplification) - ✅ COMPLETED  
**Phase:** 3 (Testing & Refinement) - ⏳ PENDING (requires deployment)  
**Started:** 2025-11-09  
**Last Updated:** 2025-11-09  
**Architecture:** Auth logic in Auth Service (Python/FastAPI), BFF is thin proxy layer only

### Summary of Implementation

**Auth Service (Python/FastAPI):**
- Complete OTP authentication implementation with PostgreSQL
- Services: database, users, otp, jwt, sms (Twilio), email (SMTP)
- Endpoints: `/auth/request-otp`, `/auth/verify-otp`, `/auth/me`, `/auth/logout`
- Database schema: `auth.users`, `auth.otp_storage`, `auth.rate_limit`
- Configuration: `auth/AUTH_CONFIGURATION.md`

**BFF (Node.js/Express):**
- Thin proxy layer - forwards requests to Auth Service
- JWT cookie management only (receives tokens from Auth, sets in browser)
- No database access, no business logic
- Proxy endpoints: `/bff/auth/*` → `http://auth:8000/auth/*`
- Configuration: `webui/BFF_CONFIGURATION.md`

**Next Steps:**
- Deploy Auth Service with PostgreSQL
- Configure OTP delivery (Twilio SMS or SMTP)
- Test complete authentication flow
- Phase 3: Security hardening and UI/UX polish
