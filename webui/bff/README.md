# BFF (Backend for Frontend)

Express.js server that acts as the Backend for Frontend, mediating between the React UI and backend services (API, Auth).

## Purpose

- **Security**: Keep backend service URLs and tokens hidden from the browser
- **Simplicity**: Provide a clean, UI-focused API surface
- **Cookie management**: Handle JWT tokens in httpOnly cookies
- **Request aggregation**: Combine multiple backend calls when needed

## Development

```bash
# From workspace root
npm run dev:bff

# Or from bff/ folder
npm run dev
```

Runs on `http://localhost:3000` by default.

## Environment Variables

```bash
PORT=3000
NODE_ENV=development
LOG_LEVEL=info
CORS_ORIGIN=http://localhost:5173

# Backend service URLs (Docker DNS names in production)
API_BASE_URL=http://api:8000
AUTH_BASE_URL=http://auth:8000

# JWT configuration (must match Auth service)
JWT_SECRET=your-secret-key-here
JWT_COOKIE_NAME=flovify_token
```

## Routes

### Health Check
- `GET /bff/health` - Returns service health status

### Authentication (TODO)
- `POST /bff/auth/login` - Login with email/password
- `POST /bff/auth/signup` - Register new user
- `POST /bff/auth/logout` - Logout and clear cookies
- `GET /bff/auth/me` - Get current user info

### API Proxy (TODO)
- `GET /bff/workflows` - List workflows
- `GET /bff/workflows/:id` - Get workflow details
- etc.

## Architecture

```
Browser → Nginx → BFF (Express) → API/Auth (FastAPI)
          :80      :3000            :8000
```

All routes are prefixed with `/bff/` to avoid conflicts with UI routes.
