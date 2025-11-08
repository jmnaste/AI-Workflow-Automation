import { ThemeOptions } from '@mui/material/styles'

interface BrandOptions {
  primary?: string
}

// Build theme options merging brand colors
export function buildTheme(opts: BrandOptions = {}): ThemeOptions {
  const primary = opts.primary ?? '#1E6BFF' // logo-inspired blue
  return {
    palette: {
      mode: 'light',
      primary: {
        main: primary,
        light: lighten(primary, 0.2),
        dark: darken(primary, 0.3),
        contrastText: '#ffffff',
      },
      background: {
        default: '#F9FAFB',
        paper: '#FFFFFF',
      },
      divider: 'rgba(0,0,0,0.12)',
    },
    shape: { borderRadius: 8 },
    typography: {
      fontFamily: 'Inter, system-ui, Arial, sans-serif',
      h4: { fontWeight: 600 },
      body1: { fontSize: 16 },
      body2: { fontSize: 14 },
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: { textTransform: 'none', fontWeight: 500 },
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
