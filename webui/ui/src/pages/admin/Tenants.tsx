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
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import CloudIcon from '@mui/icons-material/Cloud';
import { listTenants, disconnectTenant, Tenant } from '../../lib/api/tenants';
import ConnectTenantDialog from '../../components/admin/ConnectTenantDialog';
import ConfirmDialog from '../../components/admin/ConfirmDialog';

export default function Tenants() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectDialogOpen, setConnectDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Check for OAuth callback success/error
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const success = params.get('success');
    const error = params.get('error');

    if (success === 'true') {
      setError(null);
      // Clear URL params
      window.history.replaceState({}, '', window.location.pathname);
      loadTenants();
    } else if (error) {
      setError(`OAuth error: ${error}`);
      // Clear URL params
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  // Fetch tenants on mount
  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listTenants();
      setTenants(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteClick = (tenant: Tenant) => {
    setSelectedTenant(tenant);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!selectedTenant) return;

    try {
      setDeleteLoading(true);
      await disconnectTenant(selectedTenant.id);
      await loadTenants();
      setDeleteDialogOpen(false);
      setSelectedTenant(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect tenant');
    } finally {
      setDeleteLoading(false);
    }
  };

  const getProviderLabel = (provider: string) => {
    switch (provider) {
      case 'ms365':
        return 'Microsoft 365';
      case 'google':
        return 'Google Workspace';
      default:
        return provider;
    }
  };

  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'ms365':
        return 'info';
      case 'google':
        return 'success';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
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
          Connected Accounts
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setConnectDialogOpen(true)}
        >
          Connect Account
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper>
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Provider</TableCell>
                <TableCell>Account</TableCell>
                <TableCell>Display Name</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Last Token Refresh</TableCell>
                <TableCell>Connected</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {tenants.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center">
                    <Box py={4}>
                      <CloudIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                      <Typography color="text.secondary">
                        No connected accounts yet. Click "Connect Account" to get started.
                      </Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ) : (
                tenants.map((tenant) => (
                  <TableRow key={tenant.id}>
                    <TableCell>
                      <Chip
                        label={getProviderLabel(tenant.provider)}
                        color={getProviderColor(tenant.provider)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{tenant.externalAccountId}</TableCell>
                    <TableCell>{tenant.displayName}</TableCell>
                    <TableCell>
                      <Chip
                        label="Active"
                        color="success"
                        size="small"
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      {tenant.lastRefreshedAt ? formatDate(tenant.lastRefreshedAt) : 'Never'}
                    </TableCell>
                    <TableCell>{formatDate(tenant.createdAt)}</TableCell>
                    <TableCell align="right">
                      <Tooltip title="Refresh Token">
                        <IconButton size="small" onClick={() => loadTenants()}>
                          <RefreshIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Disconnect">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleDeleteClick(tenant)}
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

      <ConnectTenantDialog
        open={connectDialogOpen}
        onClose={() => setConnectDialogOpen(false)}
      />

      <ConfirmDialog
        open={deleteDialogOpen}
        title="Disconnect Account"
        message={`Are you sure you want to disconnect ${selectedTenant?.displayName || 'this account'}? This will remove all stored credentials and access to their data.`}
        confirmLabel="Disconnect"
        confirmColor="error"
        loading={deleteLoading}
        onConfirm={handleDeleteConfirm}
        onClose={() => {
          setDeleteDialogOpen(false);
          setSelectedTenant(null);
        }}
      />
    </Box>
  );
}
