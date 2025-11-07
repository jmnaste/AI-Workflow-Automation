# Brand Assets

Place branding assets here. Expected files:

- `Flovify-logo.png` — primary logo (square, PNG). Provided via attachment; copy it to this folder.
- `favicon/` (optional) — generated favicons and PWA icons.

Conventions
- Keep original source (SVG/PNG) and export sizes.
- Name variants as `Flovify-logo-dark.png`, `Flovify-logo-light.png` if needed.
- Do not commit licensed fonts unless licenses allow redistribution.

Usage in UI
- Refer to the logo from the UI as `"/images/Flovify-logo.png"` when served from repo root, or `"/ui/images/Flovify-logo.png"` if mounted under the UI app.
- For Vite dev, place a copy in `ui/public/` or use an import from this path with your bundler’s static handling strategy.
