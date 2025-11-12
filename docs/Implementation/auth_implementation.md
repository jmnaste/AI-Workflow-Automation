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

### Database Schema (PostgreSQL) - Updated 2025-11-10
- [x] Create users table in auth schema:
  - [x] `id` (UUID, primary key)
  - [x] `email` (VARCHAR, unique, lowercase, **NOT NULL** - primary identifier)
  - [x] `phone` (VARCHAR, **nullable** - optional, E.164 format)
  - [x] `otp_preference` (VARCHAR: 'sms' or 'email', **nullable**)
  - [x] `role` (VARCHAR: 'user', 'admin', 'super-user', default 'user')
  - [x] `is_active` (BOOLEAN, default true)
  - [x] `verified_at` (TIMESTAMPTZ, nullable - set on first OTP verification)
  - [x] `created_at`, `last_login_at`, `updated_at` (TIMESTAMPTZ)
  - [x] `created_by` (UUID, nullable - references other users)
- [x] Create otp_challenges table:
  - [x] `id` (UUID, primary key)
  - [x] `user_id` (UUID, foreign key to users)
  - [x] `code_hash` (BYTEA, bcrypt hash)
  - [x] `expires_at` (TIMESTAMPTZ)
  - [x] `attempts`, `max_attempts` (INTEGER)
  - [x] `status` (VARCHAR: 'sent', 'approved', 'denied', 'expired', 'canceled')
  - [x] `sent_at`, `used_at` (TIMESTAMPTZ)
  - [x] `request_ip`, `user_agent` (TEXT, nullable)
- [x] Create rate_limits table:
  - [x] `id` (UUID, primary key)
  - [x] `subject_type` (VARCHAR: 'phone' legacy for email, 'ip')
  - [x] `subject` (VARCHAR: email or IP address)
  - [x] `window_start` (TIMESTAMPTZ)
  - [x] `window_seconds`, `count`, `limit_value` (INTEGER)

### OTP Management - Updated 2025-11-10
- [x] Create `auth/app/services/otp.py`
  - [x] Generate 6-digit OTP with secrets module
  - [x] `hash_otp(otp)` - bcrypt hashing to bytea
  - [x] `store_otp(user_id, otp, request_ip, user_agent)` - creates challenge in auth.otp_challenges, cancels old 'sent' challenges
  - [x] `validate_otp(user_id, otp)` - validates against active challenge, marks status (approved/denied/expired)
  - [x] `check_rate_limit(email, request_ip)` - email-based rate limiting using auth.rate_limits
  - [x] Rate limiting (configurable, default 3 requests per 15min)
  - [x] Max attempts tracking (8 attempts per OTP, configurable)
  - [x] Challenge status tracking: sent/approved/denied/expired/canceled
  - [x] `cleanup_expired_otps()` - marks expired challenges

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

### User Management - Updated 2025-11-10
- [x] Create `auth/app/services/users.py`
  - [x] PostgreSQL CRUD operations with dict row handling
  - [x] `find_user_by_email(email)` - case-insensitive email lookup
  - [x] `find_user_by_id(user_id)` - UUID lookup
  - [x] `create_user(email, phone=None, otp_preference=None, role='user', created_by=None)` - email-primary creation
  - [x] `update_last_login(email)`, `verify_user(email)` - timestamp updates
  - [x] `update_user(email, phone, otp_preference, role, is_active)` - field updates
  - [x] User model with: id, email, phone, otp_preference, role, is_active, verified_at, last_login_at, created_by, created_at, updated_at

### Auth Endpoints (FastAPI) - Updated 2025-11-10
- [x] Update `auth/app/main.py` with routes:
  - [x] `POST /auth/request-otp`
    - [x] Validate email with Pydantic EmailStr
    - [x] Check if user exists by email (case-insensitive)
    - [x] If new: require phone + preference, create user with role='user'
    - [x] Rate limiting check by email
    - [x] Generate and store OTP hash in otp_challenges
    - [x] Send via SMS or Email based on preference
    - [x] Return success with isNewUser flag
  - [x] `POST /auth/verify-otp`
    - [x] Validate OTP with Pydantic (6-digit pattern)
    - [x] Validate OTP by user_id against active challenge
    - [x] Check expiry, attempts, and status in database
    - [x] Generate JWT with PyJWT (userId, email, **role**)
    - [x] Update last_login_at timestamp
    - [x] Set verified_at on first verification
    - [x] Return JWT and user profile with role
  - [x] `GET /auth/me`
    - [x] Validate JWT from Authorization Bearer header
    - [x] Extract email from JWT payload
    - [x] Return user profile from database (includes role, isActive, verifiedAt)
  - [x] `POST /auth/admin/create-user`
    - [x] Validate X-Admin-Token header
    - [x] Create user with email, phone, preference, **role** (user/admin/super-user)
    - [x] Return user profile
  - [x] `POST /auth/logout`
    - [x] Return success (client clears cookie)

### JWT Implementation - Updated 2025-11-10
- [x] Create `auth/app/services/jwt.py`
  - [x] `generate_jwt(user_id, email, role)` - Sign JWT with user claims (userId, email, **role**)
  - [x] `verify_jwt(token)` - Verify and decode JWT
  - [x] 7-day expiry, HS256 algorithm
  - [x] JWT payload: `{userId, email, role, exp, iat}`
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

### Migration System - Added 2025-11-10
- [x] Create `auth/app/services/migrations.py`
  - [x] Sequential SQL file execution (0000, 0001, 0002, etc.)
  - [x] Integrated with FastAPI lifespan context
  - [x] Per-file commit with rollback on error
  - [x] Each migration manages its own history in auth.migration_history
- [x] Create `auth/migrations/0004_restructure_for_email_primary.sql`
  - [x] Restructure schema from phone-primary to email-primary
  - [x] Make email NOT NULL (primary identifier)
  - [x] Make phone nullable (optional)
  - [x] Add otp_preference column
  - [x] Rename phone_e164 → phone
  - [x] Drop phone unique constraints
  - [x] Create non-unique index on phone
  - [x] Idempotent with column existence checks
  - [x] Records migration in auth.migration_history
- [x] Update database credentials for VPS parity
  - [x] POSTGRES_DB: app_db (was flovify)
  - [x] POSTGRES_USER: app_root (was flovify)

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

### Local Testing - Completed 2025-11-10
- [x] Test SMS OTP flow (with real Twilio account and phone number)
  - [x] Admin user created: jmnaste@yahoo.ca, +15142193815, SMS preference, admin role
  - [x] OTP request successful: SMS delivered to real phone
  - [x] OTP verification successful: JWT generated with userId/email/role claims
  - [x] /auth/me endpoint working: returns user profile with role/isActive/verifiedAt
- [x] Test new user registration via admin endpoint
  - [x] POST /auth/admin/create-user with X-Admin-Token header
  - [x] User created with email/phone/preference/role fields
- [x] Test full flow through web UI
  - [x] Email entry → OTP request → SMS delivery → OTP verification → JWT cookie → authenticated dashboard
  - [x] UI properly integrated with React Context for reactive auth state
- [ ] Test email OTP flow (SMS working, email configured but not tested)
- [x] Test existing user login (returning user flow working)
- [x] Test invalid OTP (attempts tracking working with "X attempts remaining" message)
- [x] Test expired OTP (status marked as 'expired' in database)
- [x] Test rate limiting (email-based rate limiting implemented)

### Security Hardening - Status 2025-11-10
- [x] Rate limit OTP requests (max 3 per 15min per email, configurable via RATE_LIMIT_MAX_REQUESTS)
- [x] Hash OTPs before storing (bcrypt with bytea storage in auth.otp_challenges)
- [x] Validate phone number format (Pydantic regex: `^\+[1-9]\d{1,14}$` for E.164)
- [x] Validate email format (Pydantic EmailStr with lowercase normalization)
- [ ] Add CSRF protection (planned for production)
- [ ] Secure JWT secret rotation plan (planned for production)

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
