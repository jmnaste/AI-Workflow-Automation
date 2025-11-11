import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  TextField,
  Button,
  Divider,
  CircularProgress,
  Alert,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import { getSystemSettings, updateSystemSettings, SystemSettings } from '../../lib/api/admin';

export default function SystemSettingsPage() {
  const [settings, setSettings] = useState<SystemSettings>({
    otpExpiry: 5,
    otpMaxAttempts: 8,
    rateLimitWindow: 15,
    rateLimitMaxRequests: 3,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSystemSettings();
      setSettings(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setError(null);
      setSuccess(false);
      await updateSystemSettings(settings);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(false)}>
          Settings updated successfully
        </Alert>
      )}

      <Typography variant="h4" component="h1" sx={{ fontWeight: 700, mb: 3 }}>
        System Settings
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          OTP Configuration
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="OTP Expiry (minutes)"
              type="number"
              value={settings.otpExpiry}
              onChange={(e) => setSettings({ ...settings, otpExpiry: parseInt(e.target.value) })}
              helperText="How long OTP codes remain valid"
              InputProps={{ inputProps: { min: 1, max: 60 } }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Attempts"
              type="number"
              value={settings.otpMaxAttempts}
              onChange={(e) => setSettings({ ...settings, otpMaxAttempts: parseInt(e.target.value) })}
              helperText="Maximum validation attempts per OTP"
              InputProps={{ inputProps: { min: 1, max: 20 } }}
            />
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        <Typography variant="h6" sx={{ mb: 2 }}>
          Rate Limiting
        </Typography>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Rate Limit Window (minutes)"
              type="number"
              value={settings.rateLimitWindow}
              onChange={(e) => setSettings({ ...settings, rateLimitWindow: parseInt(e.target.value) })}
              helperText="Time window for rate limit counting"
              InputProps={{ inputProps: { min: 1, max: 60 } }}
            />
          </Grid>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Max Requests per Window"
              type="number"
              value={settings.rateLimitMaxRequests}
              onChange={(e) => setSettings({ ...settings, rateLimitMaxRequests: parseInt(e.target.value) })}
              helperText="Maximum OTP requests per user per window"
              InputProps={{ inputProps: { min: 1, max: 20 } }}
            />
          </Grid>
        </Grid>

        <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
          >
            Save Settings
          </Button>
        </Box>
      </Paper>

      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Information
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Note: These settings are currently configured via environment variables.
          Runtime updates will be implemented in a future version.
        </Typography>
      </Paper>
    </Box>
  );
}
