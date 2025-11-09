import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline, createTheme, Box, CircularProgress } from '@mui/material';
import { buildTheme } from '../theme/theme';
import AppLayout from './AppLayout';
import Dashboard from '../pages/Dashboard';
import Workflows from '../pages/Workflows';
import Settings from '../pages/Settings';
import SignIn from '../pages/SignIn';
import { initAuth, isAuthenticated as checkAuth } from '../lib/auth.js';

const theme = createTheme(buildTheme({ primary: '#1E6BFF' }));

export default function App() {
  const [authInitialized, setAuthInitialized] = useState(false);

  useEffect(() => {
    initAuth().finally(() => setAuthInitialized(true));
  }, []);

  if (!authInitialized) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
          }}
        >
          <CircularProgress />
        </Box>
      </ThemeProvider>
    );
  }

  const isAuthenticated = checkAuth();

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route 
            path="/sign-in" 
            element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <SignIn />} 
          />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              isAuthenticated ? <AppLayout /> : <Navigate to="/sign-in" replace />
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="workflows" element={<Workflows />} />
            <Route path="settings" element={<Settings />} />
          </Route>

          {/* Catch all */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
