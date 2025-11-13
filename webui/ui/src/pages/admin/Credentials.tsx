import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Tooltip,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import KeyIcon from '@mui/icons-material/Key';
import LinkIcon from '@mui/icons-material/Link';
import { listCredentials, deleteCredential, startOAuthFlow, Credential } from '../../lib/api/credentials';
import CreateCredentialDialog from '../../components/admin/CreateCredentialDialog';
import ConfirmDialog from '../../components/admin/ConfirmDialog';

export default function Credentials() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedCredential, setSelectedCredential] = useState<Credential | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Check for OAuth callback success/error
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const successParam = params.get('success');
    const errorParam = params.get('error');

    if (successParam === 'true') {
      setSuccess('Successfully connected credential! You can now use it in workflows.');
      setError(null);
      // Clear URL params
      window.history.replaceState({}, '', window.location.pathname);
      loadCredentials();
    } else if (errorParam) {
      setError(`OAuth error: ${errorParam}`);
      setSuccess(null);
      // Clear URL params
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  // Fetch credentials on mount
  useEffect(() => {
    loadCredentials();
  }, []);

  const loadCredentials = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listCredentials();
      setCredentials(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = async (credential: Credential) => {
    try {
      // Start OAuth flow (will redirect to provider)
      await startOAuthFlow(credential.id);
      // Note: If successful, page will redirect and code below won't run
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start OAuth flow');
    }
  };

  const handleDeleteClick = (credential: Credential) => {
    setSelectedCredential(credential);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!selectedCredential) return;

    try {
      setDeleteLoading(true);
      await deleteCredential(selectedCredential.id);
      await loadCredentials();
      setDeleteDialogOpen(false);
      setSelectedCredential(null);
      setSuccess('Credential deleted successfully');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete credential');
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleCreateSuccess = () => {
    setCreateDialogOpen(false);
    loadCredentials();
    setSuccess('Credential created successfully');
  };

  const getProviderLabel = (provider: string) => {
    switch (provider) {
      case 'ms365':
        return 'Microsoft 365';
      case 'google_workspace':
        return 'Google Workspace';
      default:
        return provider;
    }
  };

  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'ms365':
        return 'info';
      case 'google_workspace':
        return 'success';
      default:
        return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'connected':
        return 'success';
      case 'error':
        return 'error';
      case 'pending':
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Credentials
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
        >
          Create Credential
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Provider</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Connected As</TableCell>
                <TableCell>Last Connected</TableCell>
                <TableCell>Created</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {credentials.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Box py={4}>
                      <KeyIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                      <Typography color="text.secondary" gutterBottom>
                        No credentials configured yet
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Create a credential to connect to Microsoft 365, Google Workspace, or other services
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ) : (
                credentials.map((credential) => (
                  <TableRow key={credential.id}>
                    <TableCell>
                      <Typography variant="body1" fontWeight="medium">
                        {credential.display_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {credential.name}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={getProviderLabel(credential.provider)}
                        color={getProviderColor(credential.provider)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={credential.status}
                        color={getStatusColor(credential.status)}
                        size="small"
                        variant="outlined"
                      />
                      {credential.error_message && (
                        <Tooltip title={credential.error_message}>
                          <Typography variant="caption" color="error" display="block">
                            Error
                          </Typography>
                        </Tooltip>
                      )}
                    </TableCell>
                    <TableCell>
                      {credential.connected_email ? (
                        <>
                          <Typography variant="body2">
                            {credential.connected_display_name || credential.connected_email}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {credential.connected_email}
                          </Typography>
                        </>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Not connected
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{formatDate(credential.last_connected_at)}</TableCell>
                    <TableCell>{formatDate(credential.created_at)}</TableCell>
                    <TableCell align="right">
                      {credential.status === 'pending' || credential.status === 'error' ? (
                        <Tooltip title="Connect via OAuth">
                          <IconButton
                            size="small"
                            color="primary"
                            onClick={() => handleConnect(credential)}
                          >
                            <LinkIcon />
                          </IconButton>
                        </Tooltip>
                      ) : null}
                      <Tooltip title="Delete">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(credential)}
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>

      <CreateCredentialDialog
        open={createDialogOpen}
        onClose={() => setCreateDialogOpen(false)}
        onSuccess={handleCreateSuccess}
      />

      <ConfirmDialog
        open={deleteDialogOpen}
        title="Delete Credential"
        message={`Are you sure you want to delete ${selectedCredential?.display_name || 'this credential'}? This will remove all stored tokens and you will need to reconnect.`}
        confirmLabel="Delete"
        confirmColor="error"
        loading={deleteLoading}
        onConfirm={handleDeleteConfirm}
        onClose={() => {
          setDeleteDialogOpen(false);
          setSelectedCredential(null);
        }}
      />
    </Box>
  );
}
