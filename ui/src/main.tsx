import React from 'react'
import ReactDOM from 'react-dom/client'
import { CssBaseline, ThemeProvider, createTheme } from '@mui/material'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import App from './shell/App'
import { buildTheme } from './theme/theme'

const queryClient = new QueryClient()

// Primary color aligned with logo blue (tunable in theme.ts)
const theme = createTheme(buildTheme({ primary: '#1E6BFF' }))

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <App />
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
