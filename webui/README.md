# WebUI — Overview and Scope

Purpose
- Build a client-facing dashboard that visualizes automation outcomes and supports Human-in-the-Loop (HITL) actions, aligned with the Platform Architecture.
- Prioritize speed-to-value and clarity: use a proven component library and theme to emulate a familiar SaaS look instead of hand-rolling styles.

Non-goals (for now)
- No bespoke design system from scratch.
- No public marketing site; the UI is internal/client-facing (authenticated) only.

High-level decisions (proposal)
- Language/runtime: TypeScript + React 18
- Dev server/build: Vite
- UI library (emulation-first): Material UI (MUI) v6 with theme overrides for brand; optional Joy UI for complementary components
- Data fetching/cache: TanStack Query
- Routing: React Router (v7+)
- Forms & validation: React Hook Form + Zod
- Auth: OIDC Authorization Code + PKCE (oidc-client-ts) against our Auth service
- HTTP client: fetch with a thin wrapper + interceptors; OpenAPI types via openapi-typescript (generated)
- State beyond server cache: minimal global state via Zustand (only where truly needed)
- Charts: Apache ECharts (rich) or Recharts (simple) — start with ECharts
- Icons: Material Icons
- Brand assets: `images/Flovify-logo.png` (primary logo), future favicon set under `images/favicon/`
- Testing: Vitest + Testing Library (unit) + Playwright (e2e)
- Lint/format: ESLint (typescript-eslint) + Prettier; TS strict
- i18n (optional later): react-i18next

Why this stack
- Emulation of a familiar, high-quality UI via MUI lowers design work and accelerates delivery.
- TanStack Query handles server state cleanly; forms + Zod give reliable UX for data entry.
- Vite provides fast local DX; React Router keeps routing mainstream and well-documented.

Initial UX primitives
- App shell with sidebar + topbar, responsive.
- Pages: Health, Workflow Run Management (list + detail), Metrics (charts), Settings.
- Reusable widgets: Status chips, DataGrid, KPI cards, Code/JSON viewer.

Path alignment
- Same-origin API access (default: `/api` through Traefik); Vite proxy for local dev.
- Authentication via OIDC (WebUI ↔ Auth service). Tokens stored in memory; refresh flows handled by oidc-client-ts.

Next steps (when we implement)
- Scaffold Vite + MUI template
- Add routing, TanStack Query provider, and OIDC auth guard
- Wire an `/api/health` ping and a WRM list mock
- Add OpenAPI type generation script
- Import and display logo in shell (sidebar header)