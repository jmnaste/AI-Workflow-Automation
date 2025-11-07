# UI Tech Stack Rationale

## Goals Mapped to Architecture
From Platform Architecture: front-office dashboard must show workflow runs, KPIs, HITL decisions, and stability metrics. We need:
- Fast iteration (developer velocity)
- Reliable data synchronization for frequently updating run lists
- Accessible theming without bespoke CSS overhead
- Clear separation of server vs client state

## Core Choices
| Concern | Choice | Reason |
|---------|--------|-------|
| Language | TypeScript | Types for API responses & form safety |
| Framework | React 18 | Ecosystem maturity; fits component-driven dashboard |
| Build/Dev | Vite | Near-instant HMR; lean config; future SSR-capable via plugins |
| UI Library | MUI (Material UI) | Production-ready components, theming, accessibility, density control |
| Styling Utilities | Emotion (under MUI) + SX prop | Avoids manually managing Tailwind purges/theme tokens initially |
| Data Fetch & Cache | TanStack Query | Automatic caching, stale/revalidate, background refetch for run lists |
| Global Lightweight State | Zustand | Simple atomic state (e.g., sidebar UI, ephemeral filters) |
| Routing | React Router | Conventional and widely supported; fine-grained route loaders optional |
| Forms | React Hook Form + Zod | Performant controlled/uncontrolled hybrid + schema validation |
| Auth | oidc-client-ts | Battle-tested OIDC flow, PKCE support; integrates with Auth service |
| API Types | openapi-typescript + generated client | Guarantees request/response correctness; reduces drift |
| Charts | ECharts | Rich visualization for KPI, latency percentiles, effectiveness trend |
| Table/Grid | MUI DataGrid | Powerful sorting/filtering/pagination with minimal setup |
| Testing (unit) | Vitest + RTL | Fast in-memory React tests |
| Testing (e2e) | Playwright | Cross-browser reliability + trace viewer |
| Lint/Format | ESLint + Prettier | Consistent style; strict mode error surfacing |
| Accessibility | Storybook (phase 2) + axe-core scans | Visual & automated a11y regression |

## Data Layer Strategy
- Server state (runs, metrics) lives purely in TanStack Query caches. Mutation and invalidation patterns:
  - `runs.list` key: refetch interval (e.g., 15s) + manual refresh button.
  - `run.detail:<id>` key: WebSocket/SSE patch updates or refetch on tab focus.
  - KPI metrics: longer cache TTL; manual invalidate on relevant mutations.
- Client ephemeral state: view filters, layout toggles in Zustand; never duplicate server data.

## Realtime Options (Phase 2)
1. Server-Sent Events (SSE) channel for run state transitions → optimistic patch of Query cache.
2. WebSocket if bidirectional interactions (e.g., live HITL approvals) escalate.
3. Fallback: short polling (10–30s) for initial milestone.

## Auth Flow
- On load, check session store for tokens.
- If absent/expired, redirect to Auth /authorize (OIDC Code + PKCE).
- Store tokens in memory (React state + browser session storage encrypted wrapper optional) to reduce XSS risk from long-lived refresh tokens.
- Auto-renew shortly before expiry; if refresh fails, force re-login.

## Theming & Branding
- Start with default MUI theme + light mode.
- Introduce `theme.ts` overrides: primary palette, typography scale, spacing.
- Token plan: colors, spacing, radius, shadow, z-index mapped to brand doc.
- Dark mode toggle added after baseline pages stabilized.

## Error & Loading UX
- Global error boundary to display fallback + session expiry hints.
- Query-level loading spinners replaced by skeletons for run list and run detail.
- Toast system for transient notifications (MUI Snackbar + central helper).

## Folder Structure (Proposed)
```
ui/
  src/
    main.tsx          # Vite entry
    app/
      providers/      # QueryClientProvider, ThemeProvider, AuthProvider
      routes/         # Route components
      layout/         # Shell (sidebar/topbar)
    features/
      runs/           # List, detail, state timeline components
      metrics/        # KPI charts, trend visualizations
      auth/           # Login callback, hooks
    components/       # Reusable primitives (tables, forms, charts, loaders)
    lib/              # API client, fetch wrappers, auth helpers
    types/            # Generated OpenAPI types
    theme/            # Theme overrides, palette, typography
    state/            # Zustand slices
    test/             # Utilities and mocks
  scripts/
    generate-openapi.ts
  README.md
```

## Security Considerations
- Avoid storing access tokens in `localStorage`; prefer in-memory or sessionStorage with rotation.
- CSRF mitigated via same-origin; ensure secure cookies for refresh if used.
- All fetch wrappers attach Authorization header; 401 triggers silent refresh then fallback to login.

## Performance Notes
- Code splitting by route and heavy chart modules.
- Memoize expensive components (charts) with stable props.
- Prefetch run detail data on hover in list.

## Testing Strategy
- Unit: component logic + hooks (query/mutation workflow).
- Integration: navigation flows (auth → run list → detail).
- E2E: login, list rendering, detail update simulation.
- Visual regression (phase 2): Storybook snapshots.

## Incremental Delivery Roadmap
1. Skeleton: Vite, routing, theme, auth stub, layout.
2. Data layer: health ping + mocked run list.
3. Real API integration (runs list/detail) + polling.
4. Metrics dashboard (static sample → live KPIs).
5. SSE/WebSocket enhancements.
6. Dark mode + accessibility refinements.
7. Storybook + design token documentation.

## Future Extensions
- Plugin surface for custom widgets per client.
- Embedding analytics (HITL trends, effectiveness delta charts).
- Offline caching (service worker) if clients need resilience.

## Deferred Alternatives
- Tailwind + shadcn/ui (possible later if full custom brand identity emerges).
- Redux Toolkit (not needed until complex cross-feature state appears).
- GraphQL (current backend REST is sufficient; avoid extra complexity early).

## Acceptance Criteria for Stack Approval
- All listed libraries have active maintenance and ≥ moderate community adoption.
- Local dev environment (install + dev server) < 2 minutes cold start.
- Ability to theme core components without ejecting or heavy overrides.
- Clean separation of server vs client state (no duplication across Query/Zustand).

---
This rationale guides initial implementation; update after milestone 3 (first live run detail view) for any adjustments.
