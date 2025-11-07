# WebUI Tech Stack Rationale

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

## Folder Structure (Proposed)
```
webui/
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
