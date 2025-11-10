import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline, createTheme, Box, CircularProgress } from '@mui/material';
import { buildTheme } from '../theme/theme';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import AppLayout from './AppLayout';
import Dashboard from '../pages/Dashboard';
import Workflows from '../pages/Workflows';
import Settings from '../pages/Settings';
import SignIn from '../pages/SignIn';

const theme = createTheme(buildTheme({ primary: '#1E6BFF' }));

function AppRoutes() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
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
    );
  }

  return (
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

      {/* Catch all - redirect to dashboard if authenticated, sign-in otherwise */}
      <Route 
        path="*" 
        element={<Navigate to={isAuthenticated ? "/dashboard" : "/sign-in"} replace />} 
      />
    </Routes>
  );
}

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  );
}
