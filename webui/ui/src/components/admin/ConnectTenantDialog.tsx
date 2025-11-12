import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Box,
  Alert,
} from '@mui/material';
import CloudIcon from '@mui/icons-material/Cloud';
import { startOAuthFlow } from '../../lib/api/tenants';

interface ConnectTenantDialogProps {
  open: boolean;
  onClose: () => void;
}

export default function ConnectTenantDialog({ open, onClose }: ConnectTenantDialogProps) {
  const [provider, setProvider] = useState<'ms365' | 'google'>('ms365');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConnect = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Get OAuth authorization URL from backend
      const authUrl = await startOAuthFlow(provider);
      
      // Redirect to OAuth provider
      window.location.href = authUrl;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start OAuth flow');
      setLoading(false);
    }
  };

  const handleClose = () => {
    setProvider('ms365');
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Connect External Account</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Connect your Microsoft 365 or Google Workspace account to enable email processing
            and automation workflows.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <FormControl fullWidth>
            <InputLabel>Provider</InputLabel>
            <Select
              value={provider}
              label="Provider"
              onChange={(e) => setProvider(e.target.value as 'ms365' | 'google')}
              disabled={loading}
            >
              <MenuItem value="ms365">
                <Box display="flex" alignItems="center" gap={1}>
                  <CloudIcon fontSize="small" />
                  Microsoft 365
                </Box>
              </MenuItem>
              <MenuItem value="google" disabled>
                <Box display="flex" alignItems="center" gap={1}>
                  <CloudIcon fontSize="small" />
                  Google Workspace (Coming Soon)
                </Box>
              </MenuItem>
            </Select>
          </FormControl>

          <Alert severity="info" sx={{ mt: 2 }}>
            You'll be redirected to {provider === 'ms365' ? 'Microsoft' : 'Google'} to authorize
            access. We only request the minimum permissions needed for email processing.
          </Alert>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleConnect}
          variant="contained"
          disabled={loading}
          startIcon={<CloudIcon />}
        >
          {loading ? 'Connecting...' : 'Connect'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
