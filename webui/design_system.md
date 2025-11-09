# WebUI Design System — Flovify

## Design Inspiration

The Flovify WebUI design is inspired by **Hostinger's Docker Manager interface**, which exemplifies modern SaaS design principles with subtle, professional styling.

### Key Design Principles

1. **Subtle Styling with Clear Contrast**
   - Clean, minimal aesthetic without losing visual hierarchy
   - Just enough contrast to distinguish between different UI sections
   - Professional appearance suitable for enterprise users

2. **Two-Level Navigation**
   - **Level 1 (Collapsed)**: Icons only with hover tooltips
   - **Level 2 (Expanded)**: Icons + page names
   - Smooth transitions between states
   - User can toggle sidebar width for more workspace

3. **Header User Section**
   - Right-aligned user controls
   - **Not authenticated**: Sign-in button
   - **Authenticated**: User avatar with dropdown menu

4. **Card-Based Layouts**
   - Content organized in clean, bordered cards
   - Minimalist style with subtle shadows
   - Proper spacing and breathing room

5. **Blue Color Scheme**
   - Primary color: `#5865f2` (Hostinger-style blue)
   - Professional, trustworthy appearance

## Technical Baseline

- **Library**: MUI (Material UI) v6
- **Mode**: Light (dark mode optional for phase 2)
- **Density**: Compact defaults for data-heavy views
- **Branding**: `images/Flovify-logo.png`

## Color Palette

### Primary Colors
- Primary main: `#5865f2` (Hostinger-style blue)
- Primary light: `#7289ff`
- Primary dark: `#4752c4`
- Primary contrast: `#ffffff`

### Background Colors
- Default: `#f5f5f7` (subtle gray)
- Paper: `#ffffff`

### Text Colors
- Primary: `#1a1a1a`
- Secondary: `#6e6e73`

### Semantic Colors
- Error: `#ff3b30`
- Warning: `#ff9500`
- Success: `#34c759`
- Info: `#5865f2`

### Dividers
- Border: `#e8e8ed`

## Typography

### Font Family
System font stack:
```
-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
```

### Type Scale
- H1: 2rem (32px), weight 600, letter-spacing -0.02em
- H2: 1.75rem (28px), weight 600, letter-spacing -0.01em
- H3-H6: 1.5rem to 1rem, weight 600
- Body1: 0.9375rem (15px), line-height 1.6
- Body2: 0.875rem (14px), line-height 1.6
- Button: 0.875rem (14px), weight 500

## Spacing & Layout

### Grid System
- 8px base unit (`theme.spacing(1) = 8px`)
- MUI responsive Grid2 with xs/sm/md/lg/xl breakpoints
- Container max-width: responsive based on breakpoint

### Border Radius
- Buttons: 6px
- Cards: 8px
- Drawer: 0px (full-height)

### Shadows
- Subtle only: `0 1px 2px 0 rgb(0 0 0 / 0.05)`
- Card hover: `0 2px 8px 0 rgb(0 0 0 / 0.08)`

---

## Layout Structure

### App Shell
- **AppBar**: Fixed header (64px) with logo, navigation breadcrumbs, user menu
- **Drawer**: Collapsible two-level sidebar
  - Collapsed: 64px width (icons only with tooltips)
  - Expanded: 240px width (icons + labels)
  - Toggle button in header
- **Main Content**: Full-height outlet with padding

### Sidebar Navigation
- Two-level structure:
  - **Top-level**: Dashboard, Workflows, Settings (icon + label)
  - **Sub-level**: Context-specific items appear based on selection
- Icons: Material Icons (Dashboard, AccountTree, Settings, etc.)
- Active state: Light blue background (`#eef0ff`)
- Hover state: Slight background change

### Header
- Left: Logo (Flovify-logo.png, ~32px height)
- Center: Page title or breadcrumbs
- Right: User menu
  - Not authenticated: "Sign In" button
  - Authenticated: Avatar with dropdown (My Account, Settings, Sign Out)

---

## Components

### Cards
```tsx
<Card sx={{ p: 3, border: 1, borderColor: 'divider' }}>
  <CardContent>...</CardContent>
</Card>
```
- Used for: Stats, activity panels, forms, content sections
- Border: 1px solid divider color
- Shadow: Subtle elevation
- Padding: 24px (`theme.spacing(3)`)

### Buttons
- Variants:
  - `contained`: Primary actions (blue background)
  - `outlined`: Secondary actions (blue border)
  - `text`: Tertiary actions (no border)
- Border radius: 6px
- Font weight: 500

### Data Display
- **Stats**: Icon + number + label in card
- **Tables**: MUI Table or DataGrid for complex data
- **Lists**: MUI List with ListItemButton for navigation
- **Chips**: For tags, status indicators
- **Tooltips**: For collapsed sidebar and helper text

### Forms
- TextField with standard variant
- React Hook Form + Zod for validation
- Error messages below fields in red

### Dialogs
- Standard MUI Dialog
- Title: Typography variant h6
- Actions: Right-aligned buttons (Cancel + Confirm)

---

## Behavioral Patterns

### Loading States
- Skeleton placeholders for content areas
- CircularProgress for async operations
- Inline spinners for button actions

### Error States
- Inline error text below form fields
- Alert banners for page-level errors
- Toast notifications for transient errors

### Empty States
- Centered icon + message + optional CTA
- Example: "No workflows yet. Create your first workflow."

### Responsive Behavior
- Mobile/tablet: Single column, collapsed sidebar by default
- Desktop: Multi-column layouts, expanded sidebar
- Breakpoints: xs (mobile), sm (tablet), md+ (desktop)

### User Menu
- Avatar clickable to open dropdown
- Menu items: My Account, Settings, Sign Out
- Sign Out triggers auth logout flow

### Sidebar Toggle
- Toggle button in header (when authenticated)
- Smooth transition animation (width change)
- State persists in localStorage (optional)

---

## Implementation

### Theme Configuration
**File**: `ui/src/theme/theme.ts`

Export `buildTheme()` function that returns MUI theme with:
- Palette overrides (primary, background, text, error, etc.)
- Typography overrides (fontFamily, type scale)
- Component overrides (MuiButton, MuiCard, MuiDrawer, etc.)
- Spacing, shape, shadows

### Layout Components
- **File**: `ui/src/shell/AppLayout.tsx` — Main shell with header, sidebar, outlet
- **File**: `ui/src/shell/Navigation.tsx` — Sidebar navigation with tooltips

### Page Components
- **File**: `ui/src/pages/Dashboard.tsx` — Example of card-based stat layout
- Other pages follow same card-based pattern

### Routing
- React Router 7 with protected routes
- Navigation state managed via router
- Outlet renders current page

### Branding Assets
- Logo: `images/Flovify-logo.png` (repo root or copy to webui/public)
- Favicon: Generate from logo and place in `images/favicon/`

---

## References

- **Design Inspiration**: [Hostinger Docker Manager UI](https://www.hostinger.com/)
- **Component Library**: [MUI v6 Documentation](https://mui.com/material-ui/)
- **Theme Customization**: [MUI Theming Guide](https://mui.com/material-ui/customization/theming/)
- **Default Theme**: [MUI Default Theme Explorer](https://mui.com/material-ui/customization/default-theme/)
- **Icons**: [Material Icons](https://mui.com/material-ui/material-icons/)
