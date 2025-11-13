import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Box,
  Alert,
  Chip,
  Stack,
  IconButton,
  InputAdornment,
} from '@mui/material';
import KeyIcon from '@mui/icons-material/Key';
import LinkIcon from '@mui/icons-material/Link';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { createCredential, startOAuthFlow, CreateCredentialRequest } from '../../lib/api/credentials';

interface CreateCredentialDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function CreateCredentialDialog({ open, onClose, onSuccess }: CreateCredentialDialogProps) {
  const [provider, setProvider] = useState<'ms365' | 'google_workspace'>('ms365');
  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [redirectUri, setRedirectUri] = useState(() => {
    // Initialize with default redirect URI
    const baseUrl = window.location.origin;
    return `${baseUrl}/bff/auth/oauth/callback`;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveAndConnect, setSaveAndConnect] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  // Set default values when provider changes
  const handleProviderChange = (newProvider: 'ms365' | 'google_workspace') => {
    setProvider(newProvider);
    
    // Set default redirect URI
    const baseUrl = window.location.origin;
    setRedirectUri(`${baseUrl}/bff/auth/oauth/callback`);
  };

  // Generate webhook endpoint URL based on provider
  const getWebhookEndpoint = () => {
    const baseUrl = window.location.origin;
    if (provider === 'ms365') {
      return `${baseUrl}/bff/auth/webhook/ms365`;
    } else if (provider === 'google_workspace') {
      return `${baseUrl}/bff/auth/webhook/google`;
    }
    return '';
  };

  // Copy webhook endpoint to clipboard
  const handleCopyWebhook = async () => {
    try {
      await navigator.clipboard.writeText(getWebhookEndpoint());
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy webhook endpoint:', err);
    }
  };

  const validateForm = () => {
    if (!name || !displayName || !clientId || !clientSecret || !redirectUri) {
      setError('All fields are required');
      return false;
    }
    
    // Validate name format (lowercase alphanumeric with hyphens)
    if (!/^[a-z0-9-]+$/.test(name)) {
      setError('Name must be lowercase alphanumeric with hyphens only (e.g., "acme-ms365")');
      return false;
    }
    
    return true;
  };

  const handleSave = async (shouldConnect: boolean) => {
    if (!validateForm()) return;

    try {
      setLoading(true);
      setError(null);
      setSaveAndConnect(shouldConnect);

      const request: CreateCredentialRequest = {
        name,
        display_name: displayName,
        provider,
        client_id: clientId,
        client_secret: clientSecret,
        redirect_uri: redirectUri,
      };

      const credential = await createCredential(request);

      if (shouldConnect) {
        // Start OAuth flow (will redirect to provider)
        await startOAuthFlow(credential.id);
        // Note: If startOAuthFlow succeeds, page will redirect and code below won't run
      } else {
        // Just created, close dialog
        handleClose();
        onSuccess();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create credential');
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (loading) return;
    
    setName('');
    setDisplayName('');
    setClientId('');
    setClientSecret('');
    setRedirectUri('');
    setProvider('ms365');
    setError(null);
    setSaveAndConnect(false);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <DialogTitle>Create OAuth Credential</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Configure OAuth credentials for connecting to external services. You'll need to
            register an OAuth application in your provider's admin console first.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Stack spacing={2.5}>
            {/* Provider Selection */}
            <FormControl fullWidth>
              <InputLabel>Provider</InputLabel>
              <Select
                value={provider}
                label="Provider"
                onChange={(e) => handleProviderChange(e.target.value as 'ms365' | 'google_workspace')}
                disabled={loading}
              >
                <MenuItem value="ms365">
                  <Box display="flex" alignItems="center" gap={1}>
                    <KeyIcon fontSize="small" />
                    Microsoft 365
                  </Box>
                </MenuItem>
                <MenuItem value="google_workspace">
                  <Box display="flex" alignItems="center" gap={1}>
                    <KeyIcon fontSize="small" />
                    Google Workspace
                  </Box>
                </MenuItem>
              </Select>
            </FormControl>

            {/* Name (slug) */}
            <TextField
              fullWidth
              label="Credential Name"
              placeholder="acme-ms365"
              value={name}
              onChange={(e) => setName(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
              disabled={loading}
              helperText="Unique identifier (lowercase, alphanumeric, hyphens only)"
            />

            {/* Display Name */}
            <TextField
              fullWidth
              label="Display Name"
              placeholder="Acme Corp Microsoft 365"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              disabled={loading}
              helperText="Human-readable name shown in UI"
            />

            {/* Client ID */}
            <TextField
              fullWidth
              label="Client ID"
              placeholder="12345678-1234-1234-1234-123456789012"
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              disabled={loading}
              helperText="OAuth application client ID from provider"
            />

            {/* Client Secret */}
            <TextField
              fullWidth
              label="Client Secret"
              type="password"
              placeholder="Enter client secret"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              disabled={loading}
              helperText="OAuth application client secret (will be encrypted)"
            />

            {/* Redirect URI */}
            <TextField
              fullWidth
              label="Redirect URI"
              placeholder="https://console.flovify.ca/bff/auth/oauth/callback"
              value={redirectUri}
              onChange={(e) => setRedirectUri(e.target.value)}
              disabled={loading}
              helperText="OAuth callback URL (must match provider configuration)"
            />

            {/* Webhook Endpoint (read-only with copy button) */}
            <TextField
              fullWidth
              label="Webhook Endpoint"
              value={getWebhookEndpoint()}
              disabled={loading}
              helperText="Use this URL for webhook subscriptions in provider console"
              InputProps={{
                readOnly: true,
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={handleCopyWebhook}
                      edge="end"
                      size="small"
                      color={copySuccess ? 'success' : 'default'}
                      title="Copy webhook endpoint"
                    >
                      <ContentCopyIcon fontSize="small" />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
            />

            <Alert severity="info" icon={<KeyIcon />}>
              <Typography variant="body2" fontWeight="medium" gutterBottom>
                {provider === 'ms365' ? 'Microsoft Azure' : 'Google Cloud Console'} Setup Required
              </Typography>
              <Typography variant="caption">
                Register an OAuth app in your {provider === 'ms365' ? 'Azure' : 'Google'} admin console
                with the redirect URI above. Required scopes:{' '}
                {provider === 'ms365' ? (
                  <Chip label="Mail.Read, Mail.Send, User.Read, offline_access" size="small" sx={{ ml: 0.5 }} />
                ) : (
                  <Chip label="gmail.readonly, gmail.send, userinfo.email" size="small" sx={{ ml: 0.5 }} />
                )}
              </Typography>
            </Alert>
          </Stack>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={() => handleSave(false)}
          variant="outlined"
          disabled={loading}
          startIcon={<KeyIcon />}
        >
          Save Only
        </Button>
        <Button
          onClick={() => handleSave(true)}
          variant="contained"
          disabled={loading}
          startIcon={<LinkIcon />}
        >
          {loading && saveAndConnect ? 'Connecting...' : 'Save & Connect'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
