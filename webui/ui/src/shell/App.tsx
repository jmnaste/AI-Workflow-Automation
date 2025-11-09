import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline, createTheme } from '@mui/material';
import { buildTheme } from '../theme/theme';
import AppLayout from './AppLayout';
import Dashboard from '../pages/Dashboard';
import Workflows from '../pages/Workflows';
import Settings from '../pages/Settings';
import SignIn from '../pages/SignIn';

const theme = createTheme(buildTheme({ primary: '#1E6BFF' }));

export default function App() {
  // TODO: Replace with actual auth check
  const isAuthenticated = true;

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/signin" element={<SignIn />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              isAuthenticated ? <AppLayout /> : <Navigate to="/signin" replace />
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
