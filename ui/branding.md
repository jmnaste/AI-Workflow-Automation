# Branding Guidelines (Flovify)

## Assets
- Primary logo: `images/Flovify-logo.png` (square). Add the provided PNG to this exact path.
- Optional variants: `Flovify-logo-dark.png`, `Flovify-logo-light.png` if needed.
- Favicon set (recommended): place under `images/favicon/`.

## Usage
- App shell: display logo at 24–32px height in sidebar header/topbar.
- Maintain clear space equal to the height of the "F" cap around the logo when used standalone.
- Do not distort or recolor outside theme tokens; dark mode should use the light variant if necessary.

## Favicon / PWA Icons
Generate from the PNG using any of the following tools (pick one):
- realfavicongenerator.net
- favicon.io
- pwa-asset-generator

Place outputs in `images/favicon/` with at least:
- `favicon.ico`
- `favicon-32x32.png`
- `favicon-16x16.png`
- `apple-touch-icon.png`
- `site.webmanifest` (optional for PWA)

## Theme Mapping
- Map logo blue to `theme.palette.primary.main`.
- Derive complementary shades for `primary.light` and `primary.dark`.
- Ensure text/icon contrast meets WCAG AA on primary surfaces.

## File Locations (dev vs prod)
- Development (Vite): consider copying the logo into `ui/public/` for static serving at the app base path. Alternatively, import the image via bundler if tree-shaking desired.
- Production: serve from `/images/Flovify-logo.png` behind Traefik or the static files handler for the UI container.

## Change Control
- Keep original source assets (SVG/hi-res PNG) if available.
- Document changes (size, palette adjustments) in this file with date and reason.
