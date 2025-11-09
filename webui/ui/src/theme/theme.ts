import { ThemeOptions } from '@mui/material/styles'

interface BrandOptions {
  primary?: string
}

// Build theme options with Hostinger-inspired subtle design
export function buildTheme(opts: BrandOptions = {}): ThemeOptions {
  const primary = opts.primary ?? '#5865f2' // Hostinger-style blue
  return {
    palette: {
      mode: 'light',
      primary: {
        main: primary,
        light: lighten(primary, 0.15),
        dark: darken(primary, 0.2),
        contrastText: '#ffffff',
      },
      secondary: {
        main: primary,
        light: lighten(primary, 0.15),
        dark: darken(primary, 0.2),
        contrastText: '#ffffff',
      },
      background: {
        default: '#f5f5f7',
        paper: '#ffffff',
      },
      text: {
        primary: '#1a1a1a',
        secondary: '#6e6e73',
      },
      divider: '#e8e8ed',
      error: { main: '#ff3b30' },
      warning: { main: '#ff9500' },
      success: { main: '#34c759' },
      info: { main: primary },
    },
    shape: { borderRadius: 6 },
    typography: {
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      h1: { fontWeight: 600, fontSize: '2rem', letterSpacing: '-0.02em' },
      h2: { fontWeight: 600, fontSize: '1.75rem', letterSpacing: '-0.01em' },
      h3: { fontWeight: 600, fontSize: '1.5rem' },
      h4: { fontWeight: 600, fontSize: '1.25rem' },
      h5: { fontWeight: 600, fontSize: '1.125rem' },
      h6: { fontWeight: 600, fontSize: '1rem' },
      body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
      body2: { fontSize: '0.875rem', lineHeight: 1.6 },
      button: { textTransform: 'none', fontWeight: 500, fontSize: '0.875rem' },
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            padding: '7px 14px',
            boxShadow: 'none',
            '&:hover': { boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)' },
          },
          outlined: { borderColor: '#e8e8ed' },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
            borderRadius: 8,
            border: '1px solid #e8e8ed',
          },
        },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: {
            borderRight: '1px solid #e8e8ed',
            backgroundColor: '#fafafa',
          },
        },
      },
      MuiAppBar: {
        styleOverrides: {
          root: { boxShadow: '0 1px 0 0 #e8e8ed' },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            margin: '2px 8px',
            '&.Mui-selected': {
              backgroundColor: primary,
              color: '#ffffff',
              '&:hover': { backgroundColor: darken(primary, 0.1) },
              '& .MuiListItemIcon-root': { color: '#ffffff' },
            },
            '&:hover': { backgroundColor: 'rgba(88, 101, 242, 0.08)' },
          },
        },
      },
      MuiContainer: {
        defaultProps: { maxWidth: 'lg' },
      },
    },
  }
}

function lighten(hex: string, amt: number) {
  return adjust(hex, amt)
}
function darken(hex: string, amt: number) {
  return adjust(hex, -amt)
}

function adjust(hex: string, amt: number) {
  const c = hex.replace('#', '')
  const num = parseInt(c, 16)
  let r = (num >> 16) + Math.round(255 * amt)
  let g = ((num >> 8) & 0x00ff) + Math.round(255 * amt)
  let b = (num & 0x0000ff) + Math.round(255 * amt)
  r = Math.min(255, Math.max(0, r))
  g = Math.min(255, Math.max(0, g))
  b = Math.min(255, Math.max(0, b))
  return '#' + (r << 16 | g << 8 | b).toString(16).padStart(6, '0')
}
