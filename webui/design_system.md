# WebUI Design System (Emulation-first)

Goal
- Deliver a polished, enterprise-ready look by emulating a familiar SaaS visual language using a mature component library, not bespoke CSS.

Baseline
- Library: MUI (Material UI) v6
- Mode: Light first, Dark optional (phase 2)
- Density: Compact defaults for data-heavy views (DataGrid, tables)
- Branding asset: `images/Flovify-logo.png` (primary logo). Keep variants for dark/light if needed.

Foundations (Tokens)
- Color
  - Primary: brand color (to be defined) + tonal scale via MUI palette
  - Secondary: neutral accent; success/warning/error standard MUI hues
  - Surface: subtle elevations; low-contrast backgrounds for cards/sections
- Typography
  - Base: system font stack or Inter
  - Scale: 12, 14, 16, 20, 24, 32 for body/labels/headers
  - Weights: 400/500/600 common; avoid excessive bolds
- Spacing
  - 8px grid (unit = 8)
  - Compact paddings in tables/forms; generous in page headers
- Radius & Elevation
  - Radius: 6–8px on cards, inputs, buttons
  - Shadows: low and medium only; avoid heavy drop shadows

Layout
- App Shell: left sidebar + topbar; responsive collapse below md
- Content: max-width containers for readability; full-width grids for WRM list
- Page templates
  - Health: KPI cards + recent events
  - Workflow Runs
    - List: filters, status chips, sort, pagination; quick prefetch on hover
    - Detail: header (id, status, timestamps, actor); tabs (timeline, inputs/outputs, logs)
  - Metrics: charts (p95 latency, effectiveness trend, error rate), time range selector
  - Settings: profiles, tokens, connections (n8n), theme toggle (phase 2)

Components (Preferred)
- Navigation: Drawer, AppBar, Breadcrumbs
- Inputs: TextField, Select, Autocomplete, Switch, Date/Time pickers
- Data: DataGrid, Table, Chip, Tooltip, Badge, Dialog
- Feedback: Snackbar (central toast helper), Backdrop, Skeleton
- Display: Card, Paper, Typography, Tabs, Accordion
- Icons: Material Icons (Outlined)

Behavioral Patterns
- Loading → Skeletons then content; avoid spinner-only views
- Errors → Inline callouts with retry; auth errors route to login
- Long lists → Virtualized where needed (DataGrid); enable column persistence
- Accessibility → Focus outlines preserved; labels and aria-* added; color contrast meets WCAG AA

Branding Hooks
- `theme.ts`: override palette, typography, shape, components density
- Global CSS reset: MUI CssBaseline with minor variable tweaks
- Logo path: reference "/images/Flovify-logo.png" (repo root) or copy into WebUI public for app-relative serving
- Favicon: generate from the logo (see webui/branding.md) and place in `images/favicon/`

Theming Workflow
1. Start with default theme; implement pages using stock MUI components.
2. Introduce `theme.ts` with palette and typography adjustments.
3. Add dark mode once core flows stable.
4. Extract token documentation into Storybook (phase 2).

Alternatives (not default)
- DaisyUI (Tailwind plugin) for rapid theme switching if we pivot to Tailwind.
- shadcn/ui for bespoke branding (requires Tailwind + more custom work).

References
- MUI Templates (Dashboard, Minimal) for layout inspiration (do not copy assets).
- MUI X DataGrid docs for virtualization and performance patterns.
