# WebUI Architecture — Frontend + BFF Pattern

## Overview

The WebUI is a single-container deployment combining:
- **Frontend:** React 18 + TypeScript SPA (static files served by Nginx)
- **Backend for Frontend (BFF):** Node.js + Express + TypeScript (business logic, auth, orchestration)

This architecture provides clean separation between presentation and business logic while keeping deployment simple.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ HTTPS (TLS)
                               ↓
                    ┌──────────────────────┐
                    │      Traefik         │
                    │  (Reverse Proxy)     │
                    │  - TLS termination   │
                    │  - Let's Encrypt     │
                    └──────────┬───────────┘
                               │
                               │ HTTP (internal)
                               ↓
                    ┌──────────────────────┐
                    │   Nginx (port 80)    │
                    │   Route by path:     │
                    │   /       → SPA      │
                    │   /bff/*  → Express  │
                    │   /images → static   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                  │
              ↓                                  ↓
    ┌─────────────────┐              ┌─────────────────────┐
    │  React SPA      │              │  Node.js Express    │
    │  (TypeScript)   │              │  BFF (TypeScript)   │
    │                 │              │  port 3000          │
    │  - Presentation │              │  - Auth logic       │
    │  - UI logic     │              │  - Session mgmt     │
    │  - No secrets   │              │  - API aggregation  │
    └─────────────────┘              └──────────┬──────────┘
                                                 │
                                                 │ Private Docker network
                                                 │
                       ┌─────────────────────────┴─────────────────────┐
                       │                                                │
                       ↓                                                ↓
              ┌──────────────────┐                           ┌──────────────────┐
              │   API Service    │                           │  Auth Service    │
              │   (Python/       │                           │  (Python/        │
              │    FastAPI)      │                           │   FastAPI)       │
              │                  │                           │                  │
              │  - LangChain     │                           │  - User mgmt     │
              │  - AI workflows  │                           │  - JWT issuer    │
              │  - Business      │                           │  - Permissions   │
              │    logic         │                           │                  │
              └──────────────────┘                           └──────────────────┘
```

---

## Container Structure

```
webui container (ghcr.io/jmnaste/ai-workflow-automation/webui:main)
│
├─ Nginx (port 80)
│   ├─ Serves static React build
│   ├─ Proxies /bff/* to Express
│   └─ Configuration: /etc/nginx/conf.d/default.conf
│
├─ Node.js Express BFF (port 3000)
│   ├─ TypeScript source: /app/bff/
│   ├─ Compiled JS: /app/bff/dist/
│   ├─ Dependencies: package.json, node_modules
│   └─ Process manager: PM2 or direct node
│
└─ React SPA
    ├─ Built files: /usr/share/nginx/html/
    ├─ Static assets: /usr/share/nginx/html/images/
    └─ index.html, *.js, *.css
```

---

## Request Flow Examples

### Example 1: User Visits Homepage

```
1. Browser → https://console.flovify.ca/
                ↓
2. Traefik → routes to webui container (Host: console.flovify.ca)
                ↓
3. Nginx → location / → serves /usr/share/nginx/html/index.html
                ↓
4. Browser ← HTML + JS + CSS (React app)
                ↓
5. React app boots, renders UI
```

### Example 2: User Logs In

```
1. Browser → POST https://console.flovify.ca/bff/auth/login
            { email, password }
                ↓
2. Traefik → webui container
                ↓
3. Nginx → location /bff/ → proxy to http://localhost:3000/auth/login
                ↓
4. Express → validates credentials with auth service
            fetch('http://auth:8000/auth/validate', ...)
                ↓
5. Auth service ← { email, password }
                ↓
6. Auth service → { jwt: "eyJ..." }
                ↓
7. Express ← JWT from auth service
            → Sets httpOnly cookie
            → Returns success to browser
                ↓
8. Browser ← Set-Cookie: session=jwt; HttpOnly; Secure; SameSite=Strict
```

### Example 3: User Loads Dashboard

```
1. Browser → GET https://console.flovify.ca/bff/dashboard
            Cookie: session=jwt
                ↓
2. Traefik → webui container
                ↓
3. Nginx → /bff/dashboard → Express
                ↓
4. Express → validates JWT from cookie
            → extracts user ID
            → calls multiple backend services in parallel
            
            Promise.all([
              fetch('http://api:8000/workflows?user_id=123'),
              fetch('http://api:8000/metrics?user_id=123'),
              fetch('http://auth:8000/user/123/permissions')
            ])
                ↓
5. Backend services (api, auth) ← requests with user context
                ↓
6. Backend services → responses
                ↓
7. Express ← aggregated data
            → transforms/shapes for frontend
            → returns single JSON response
                ↓
8. Browser ← { workflows: [...], metrics: {...}, permissions: [...] }
                ↓
9. React renders dashboard with aggregated data
```

### Example 4: Direct API Call (Bypassed — Not Allowed)

```
1. Browser → GET https://console.flovify.ca/api/workflows
                ↓
2. Traefik → webui container
                ↓
3. Nginx → location /api/ would proxy to http://api:8000/
                ↓
   ❌ We REMOVE this route from nginx.conf
   ❌ All backend access must go through BFF
   ❌ Browser gets 404 Not Found
```

---

## Security Model

### Authentication Flow

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │ 1. POST /bff/auth/login { email, password }
       ↓
┌──────────────────┐
│  Express BFF     │
│  (validates)     │
└──────┬───────────┘
       │ 2. POST http://auth:8000/auth/validate
       ↓
┌──────────────────┐
│  Auth Service    │
│  (checks creds)  │
└──────┬───────────┘
       │ 3. Returns JWT
       ↓
┌──────────────────┐
│  Express BFF     │
│  (sets cookie)   │
└──────┬───────────┘
       │ 4. Set-Cookie: session=JWT; HttpOnly; Secure
       ↓
┌─────────────┐
│   Browser   │
│  (stores)   │
└─────────────┘
```

### Subsequent Authenticated Requests

```
Browser → BFF (with cookie)
         ↓
      Validate JWT
         ↓
      Extract user ID
         ↓
      Call backend with user context
      fetch('http://api:8000/...', {
        headers: { 'X-User-ID': userId }
      })
         ↓
      Backend enforces permissions
         ↓
      Return data to browser
```

### Key Security Properties

| Layer | Security Mechanism |
|-------|--------------------|
| **Transport** | TLS (Traefik terminates HTTPS) |
| **Sessions** | Stateless JWT in httpOnly cookie (XSS-proof) |
| **CSRF** | SameSite=Strict cookie attribute |
| **Backend Access** | Private Docker network only (no public routes to api/auth) |
| **Secrets** | Never exposed to browser (BFF holds service tokens) |
| **Rate Limiting** | Traefik middleware (optional) |
| **CORS** | Same-origin (no CORS needed) |

---

## Technology Stack

### Frontend (Browser)

- **Framework:** React 18
- **Language:** TypeScript (strict mode)
- **Build Tool:** Vite
- **UI Library:** Material UI (MUI) v6
- **Data Fetching:** TanStack Query
- **Routing:** React Router v7+
- **Forms:** React Hook Form + Zod validation
- **State:** Zustand (minimal global state)
- **Charts:** Apache ECharts
- **Icons:** Material Icons
- **Testing:** Vitest + Testing Library

### Backend for Frontend (BFF)

- **Runtime:** Node.js 20+ LTS
- **Framework:** Express
- **Language:** TypeScript
- **HTTP Client:** node-fetch or undici
- **Validation:** Zod (shared with frontend)
- **JWT:** jsonwebtoken
- **Logging:** pino or winston
- **Process Manager:** PM2 (for production)
- **Testing:** Jest or Vitest

### Infrastructure

- **Web Server:** Nginx (alpine-based)
- **Container:** Docker (multi-stage build)
- **Reverse Proxy:** Traefik
- **Network:** Docker bridge network (private)
- **TLS:** Let's Encrypt (via Traefik ACME)

---

## File Structure

```
webui/
├── Dockerfile                   # Multi-stage: build React + BFF, run with Nginx
├── nginx.conf                   # Nginx config (SPA + proxy to BFF)
├── package.json                 # Root dependencies (scripts for both)
├── tsconfig.json                # Shared TypeScript config
│
├── src/                         # React Frontend
│   ├── main.tsx                 # Entry point
│   ├── shell/
│   │   ├── App.tsx              # App shell (layout, routing)
│   │   └── Router.tsx           # Route definitions
│   ├── pages/                   # Page components
│   │   ├── Dashboard.tsx
│   │   ├── WorkflowList.tsx
│   │   └── Login.tsx
│   ├── components/              # Reusable UI components
│   ├── hooks/                   # Custom React hooks
│   ├── services/                # API client for /bff/* endpoints
│   │   └── bffClient.ts         # fetch('/bff/...')
│   ├── theme/                   # MUI theme config
│   └── types/                   # TypeScript types (shared with BFF)
│
├── bff/                         # Backend for Frontend (Express)
│   ├── package.json             # BFF-specific dependencies
│   ├── tsconfig.json            # BFF TypeScript config
│   ├── src/
│   │   ├── index.ts             # Express app entry point
│   │   ├── routes/              # Route handlers
│   │   │   ├── auth.ts          # /bff/auth/*
│   │   │   ├── dashboard.ts     # /bff/dashboard
│   │   │   └── workflows.ts     # /bff/workflows/*
│   │   ├── middleware/          # Express middleware
│   │   │   ├── auth.ts          # JWT validation
│   │   │   ├── errors.ts        # Error handling
│   │   │   └── logging.ts       # Request logging
│   │   ├── services/            # Backend communication
│   │   │   ├── apiClient.ts     # Calls http://api:8000
│   │   │   └── authClient.ts    # Calls http://auth:8000
│   │   ├── types/               # TypeScript types
│   │   └── utils/               # Helpers (JWT, validation, etc.)
│   └── dist/                    # Compiled JavaScript (build output)
│
├── images/                      # Static assets
│   ├── Flovify-logo.png
│   └── favicon/
│
├── webui.compose.yml            # VPS deployment (Hostinger)
├── local.compose.yml            # Local development
├── README.md                    # Deployment guide
└── ARCHITECTURE.md              # This file
```

---

## Build & Deployment

### Multi-Stage Dockerfile

```dockerfile
# Stage 1: Build React frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY src/ ./src/
COPY tsconfig.json vite.config.ts index.html ./
RUN npm run build
# Output: /app/dist/ (static files)

# Stage 2: Build BFF backend
FROM node:20-alpine AS bff-builder
WORKDIR /app/bff
COPY bff/package*.json ./
RUN npm ci
COPY bff/src/ ./src/
COPY bff/tsconfig.json ./
RUN npm run build
# Output: /app/bff/dist/ (compiled JS)

# Stage 3: Production runtime
FROM nginx:alpine
# Install Node.js for BFF
RUN apk add --no-cache nodejs npm

# Copy frontend build
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Copy BFF build
COPY --from=bff-builder /app/bff/dist /app/bff/dist
COPY --from=bff-builder /app/bff/node_modules /app/bff/node_modules

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets
COPY images /usr/share/nginx/html/images

# Start both Nginx and BFF
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh
CMD ["/docker-entrypoint.sh"]
```

### docker-entrypoint.sh

```bash
#!/bin/sh
# Start BFF in background
node /app/bff/dist/index.js &

# Start Nginx in foreground
nginx -g 'daemon off;'
```

---

## Development Workflow

### Local Development

```bash
# Terminal 1: Run Vite dev server (React)
cd webui
npm run dev
# Access: http://localhost:5173

# Terminal 2: Run BFF dev server (Express)
cd webui/bff
npm run dev
# Runs on: http://localhost:3000

# Vite proxy config forwards /bff/* to localhost:3000
```

### Build & Test Locally

```bash
# Build everything
docker build -t webui-test .

# Run locally
docker run --rm -p 8080:80 webui-test

# Test
curl http://localhost:8080/ui/health
curl http://localhost:8080/bff/health
```

### Deploy to VPS

1. Push to GitHub → triggers workflow
2. Workflow builds image → pushes to GHCR
3. On Hostinger: redeploy webui container
4. Traefik routes `https://console.flovify.ca` → webui

---

## External Integrations: OAuth Webhooks

### Microsoft 365 & Google Workspace Integration

The application integrates with Microsoft 365 and Google Workspace for:
- Email management (download, send)
- Document operations (OneDrive, Google Drive)
- Calendar and contacts
- Real-time event notifications

**OAuth Callback Strategy:** OAuth callbacks are handled by the **BFF** with provider-specific routes that forward to the **Auth service**.

```
Microsoft/Google OAuth
  ↓ https://console.flovify.ca/bff/auth/webhook/{provider}
  ↓
Traefik → WebUI (Nginx) → BFF (Express)
  ↓ Forward with query params
Auth Service: /auth/oauth/callback
  ↓
Auth validates, exchanges code for tokens
  ↓
Stores encrypted tokens in auth.credential_tokens
  ↓
Redirects to UI success page
```

**Architecture Rationale:**
- ✅ **Separation of concerns**: BFF handles public-facing OAuth callbacks, Auth handles backend token exchange
- ✅ **Provider extensibility**: Easy to add new providers (`/bff/auth/webhook/salesforce`, `/bff/auth/webhook/slack`)
- ✅ **Single domain**: OAuth callbacks on same domain as UI (no CORS issues)
- ✅ **Auth service remains private**: No public exposure needed
- ✅ **Credential-based**: Multiple OAuth apps per provider supported

**BFF OAuth Routes:**
- `/bff/auth/webhook/ms365` → Forwards to Auth `/auth/oauth/callback`
- `/bff/auth/webhook/googlews` → Forwards to Auth `/auth/oauth/callback`
- `/bff/auth/oauth/callback` → Generic fallback route

**External Service Configuration (Azure/Google):**
```
Microsoft 365: Redirect URI = https://console.flovify.ca/bff/auth/webhook/ms365
Google Workspace: Redirect URI = https://console.flovify.ca/bff/auth/webhook/googlews
```

**Credentials Model:**
Each credential stores its own OAuth app configuration:
- `client_id`, `client_secret`: OAuth app credentials
- `redirect_uri`: Provider-specific callback URL
- `tenant_id`: (Optional) Azure AD tenant ID for single-tenant apps
- `scopes`: Permissions requested
- Multiple credentials per provider allowed (testing, different tenants, etc.)

---

## API Contracts

### BFF Endpoints (Frontend → BFF)

| Method | Path | Purpose | Auth Required |
|--------|------|---------|---------------|
| POST | `/bff/auth/request-otp` | Request OTP for login | No |
| POST | `/bff/auth/verify-otp` | Verify OTP and login | No |
| POST | `/bff/auth/logout` | Clear session | Yes |
| GET | `/bff/auth/me` | Get current user info | Yes |
| GET | `/bff/auth/credentials` | List OAuth credentials | Yes (admin) |
| POST | `/bff/auth/credentials` | Create OAuth credential | Yes (admin) |
| GET | `/bff/auth/oauth/authorize?credential_id=xxx` | Get OAuth authorization URL | Yes (admin) |
| GET | `/bff/auth/webhook/ms365` | MS365 OAuth callback | No (public) |
| GET | `/bff/auth/webhook/googlews` | Google Workspace OAuth callback | No (public) |
| GET | `/bff/dashboard` | Aggregate dashboard data | Yes |
| GET | `/bff/workflows` | List workflows for user | Yes |
| POST | `/bff/workflows` | Create new workflow | Yes |
| GET | `/bff/workflows/:id` | Get workflow details | Yes |

### BFF → Backend Communication

| BFF Calls | Backend Service | Headers |
|-----------|-----------------|---------|
| `http://auth:8000/auth/validate` | Auth | `X-Service-Token` or forward JWT |
| `http://auth:8000/user/:id` | Auth | Forward user JWT |
| `http://api:8000/workflows` | API | `X-User-ID: <user_id>` |
| `http://api:8000/metrics` | API | `X-User-ID: <user_id>` |

### BFF OAuth Callback Routes (Public)

| Method | Path | Purpose | Public |
|--------|------|---------|--------|
| GET | `/bff/auth/webhook/ms365` | Microsoft 365 OAuth callback | Yes (via console.flovify.ca) |
| GET | `/bff/auth/webhook/googlews` | Google Workspace OAuth callback | Yes (via console.flovify.ca) |
| GET | `/bff/auth/oauth/callback` | Generic OAuth callback (fallback) | Yes (via console.flovify.ca) |

**Note**: All BFF OAuth callbacks forward to Auth service `/auth/oauth/callback` for token exchange.

---

## Environment Variables

### Hostinger VPS Configuration

```env
# Traefik network
TRAEFIK_NETWORK=root_default

# Public domain
UI_HOST=console.flovify.ca

# Traefik TLS
UI_ENTRYPOINTS=websecure
TRAEFIK_CERT_RESOLVER=letsencrypt

# Runtime
NODE_ENV=production

# BFF configuration (optional, hardcoded in image)
BFF_PORT=3000
API_BASE_URL=http://api:8000
AUTH_BASE_URL=http://auth:8000
```

---

## Migration Path

### Current State (Before BFF)
- ❌ Frontend calls `/api/*` and `/auth/*` directly via Nginx proxy
- ❌ No business logic layer
- ❌ Auth logic scattered in frontend

### Target State (With BFF)
- ✅ Frontend calls `/bff/*` only
- ✅ BFF handles auth, aggregation, transformation
- ✅ Backend services remain private
- ✅ Clean separation of concerns

### Migration Steps

1. **Phase 1:** Add BFF to container, keep existing `/api` and `/auth` proxies
2. **Phase 2:** Implement `/bff/auth/*` endpoints, migrate login flow
3. **Phase 3:** Implement `/bff/dashboard`, migrate dashboard page
4. **Phase 4:** Migrate remaining pages one by one
5. **Phase 5:** Remove `/api` and `/auth` proxy routes from nginx.conf
6. **Phase 6:** Add rate limiting, caching, monitoring to BFF

---

## Observability

### Health Checks

- **Nginx:** `GET /ui/health` → `200 {"status":"ok"}`
- **BFF:** `GET /bff/health` → `200 {"status":"ok","uptime":123}`
- **Combined:** Both must return 200 for container to be healthy

### Logging Strategy

```javascript
// BFF logs (structured JSON)
logger.info({
  msg: 'Dashboard request',
  userId: req.user.id,
  duration: 145,
  backendCalls: ['api/workflows', 'api/metrics']
});
```

### Metrics to Track

- Request count by endpoint
- Response time (p50, p95, p99)
- Error rate by type
- Backend call success/failure rate
- Active sessions

---

## Security Checklist

- [x] TLS enforced (Traefik)
- [x] HttpOnly cookies (XSS prevention)
- [x] SameSite=Strict (CSRF prevention)
- [x] JWT validation in BFF
- [x] No secrets in frontend code
- [x] Backend services private (no public routes)
- [x] User context forwarded to backend
- [ ] Rate limiting (TODO: Traefik middleware)
- [ ] Input validation (TODO: Zod schemas in BFF)
- [ ] CORS headers (not needed, same-origin)
- [ ] Content Security Policy (TODO: nginx headers)

---

## Performance Considerations

### Frontend Optimization

- Code splitting (Vite automatic)
- Lazy route loading
- Asset compression (gzip in Nginx)
- Image optimization (WebP, srcset)
- React.memo for expensive renders
- TanStack Query for caching

### BFF Optimization

- Parallel backend calls (`Promise.all`)
- Request deduplication (TanStack Query server-side)
- Response compression (Express middleware)
- Keep-alive connections to backend
- Circuit breaker pattern (future: resilience4j-style)

### Nginx Optimization

- Gzip compression (already configured)
- Browser caching headers for static assets
- HTTP/2 support (via Traefik)

---

## Future Enhancements

### Short Term
- [ ] Add request ID tracing (X-Request-ID)
- [ ] Implement refresh token flow
- [ ] Add BFF request/response logging
- [ ] Set up Prometheus metrics export

### Medium Term
- [ ] Split into two containers (webui + bff)
- [ ] Add Redis for session storage
- [ ] Implement rate limiting per user
- [ ] Add circuit breaker for backend calls

### Long Term
- [ ] GraphQL layer in BFF (optional)
- [ ] Server-Sent Events for real-time updates
- [ ] gRPC between BFF ↔ backends (if latency becomes issue)
- [ ] Multi-tenant support

---

## Summary

This architecture balances:

✅ **Simplicity:** Single container, familiar tech stack  
✅ **Security:** Private backends, controlled access through BFF  
✅ **Scalability:** Can split containers later as needed  
✅ **Maintainability:** Clear separation between UI and business logic  
✅ **Developer Experience:** TypeScript everywhere, shared types  

The BFF pattern gives us flexibility to evolve the backend without breaking the frontend, while keeping deployment simple for the MVP phase.

