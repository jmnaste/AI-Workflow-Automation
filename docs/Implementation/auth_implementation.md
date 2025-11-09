# Authentication Implementation - OTP-based Passwordless Login

## Overview
Implement passwordless authentication using OTP (One-Time Password) delivered via SMS (Twilio) or Email.

## User Flow
1. User enters email
2. System checks if user exists:
   - **New user**: Collect phone number and OTP delivery preference (SMS/Email)
   - **Existing user**: Use saved preference
3. System generates and sends 6-digit OTP
4. User enters OTP
5. System validates OTP and issues JWT token

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

## Phase 2: BFF Implementation

### Dependencies
- [ ] Install Twilio SDK: `npm install twilio`
- [ ] Install email library: `npm install nodemailer`
- [ ] Install JWT library: `npm install jsonwebtoken @types/jsonwebtoken`
- [ ] Install bcrypt for OTP hashing: `npm install bcrypt @types/bcrypt`

### OTP Management
- [ ] Create `bff/src/services/otp.ts`
  - [ ] Generate 6-digit OTP
  - [ ] Store OTP with expiry (in-memory Map, 5min TTL)
  - [ ] Validate OTP
  - [ ] Rate limiting (max 3 attempts)

### Twilio Integration
- [ ] Create `bff/src/services/sms.ts`
  - [ ] Initialize Twilio client
  - [ ] Send SMS function
  - [ ] Error handling

### Email Integration
- [ ] Create `bff/src/services/email.ts`
  - [ ] Configure nodemailer
  - [ ] Send OTP email function
  - [ ] Email template

### User Storage
- [ ] Create `bff/src/services/users.ts`
  - [ ] Simple JSON file or SQLite for user profiles
  - [ ] CRUD operations: findByEmail, create, update
  - [ ] Store: email, phone, otpPreference, createdAt

### Auth Endpoints
- [ ] Create `bff/src/routes/auth.ts`
  - [ ] `POST /bff/auth/request-otp`
    - [ ] Validate email format
    - [ ] Check if user exists
    - [ ] If new: validate phone + preference
    - [ ] Generate OTP
    - [ ] Send via SMS or Email
    - [ ] Return success/error
  - [ ] `POST /bff/auth/verify-otp`
    - [ ] Validate OTP
    - [ ] Check expiry and attempts
    - [ ] Generate JWT
    - [ ] Set httpOnly cookie
    - [ ] Return user profile
  - [ ] `GET /bff/auth/me`
    - [ ] Validate JWT from cookie
    - [ ] Return user profile
  - [ ] `POST /bff/auth/logout`
    - [ ] Clear JWT cookie
    - [ ] Return success

### JWT Implementation
- [ ] Create `bff/src/middleware/jwt.ts`
  - [ ] Sign JWT with user claims
  - [ ] Verify JWT middleware
  - [ ] Extract user from token

### Environment Variables
- [ ] Add to webui.compose.yml and README:
  ```
  TWILIO_ACCOUNT_SID=...
  TWILIO_AUTH_TOKEN=...
  TWILIO_PHONE_NUMBER=...
  SMTP_HOST=...
  SMTP_PORT=587
  SMTP_USER=...
  SMTP_PASS=...
  SMTP_FROM=noreply@flovify.ca
  OTP_EXPIRY_MINUTES=5
  OTP_MAX_ATTEMPTS=3
  ```

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
**Phase:** 1 (UI Implementation)  
**Started:** 2025-11-09  
**Last Updated:** 2025-11-09
