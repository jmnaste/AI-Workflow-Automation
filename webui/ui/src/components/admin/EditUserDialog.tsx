import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  MenuItem,
  Grid,
  FormControl,
  InputLabel,
  Select,
  FormControlLabel,
  Switch,
} from '@mui/material';
import { AdminUser } from '../../lib/api/admin';

/**
 * User Role Definitions:
 * - user: Standard user with basic access
 * - super: Elevated user with additional business workflow privileges (NO admin console access)
 * - admin: Full administrative access including admin console and user management
 * 
 * Note: Only 'admin' role can access admin console.
 */
interface EditUserDialogProps {
  open: boolean;
  user: AdminUser | null;
  onClose: () => void;
  onUpdate: (userId: string, updates: {
    email?: string;
    phone?: string;
    preference?: 'sms' | 'email' | 'none';
    role?: 'user' | 'admin' | 'super-user';
    isActive?: boolean;
  }) => Promise<void>;
}

export default function EditUserDialog({ open, user, onClose, onUpdate }: EditUserDialogProps) {
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [preference, setPreference] = useState<'sms' | 'email' | 'none' | ''>('');
  const [role, setRole] = useState<'user' | 'admin' | 'super-user'>('user');
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load user data when dialog opens
  useEffect(() => {
    if (user) {
      setEmail(user.email);
      setPhone(user.phone || '');
      setPreference((user as any).otpPreference || '');
      setRole(user.role);
      setIsActive(user.isActive);
    }
  }, [user]);

  const handleSubmit = async () => {
    setError(null);
    
    if (!user) return;

    // Validation
    if (!email) {
      setError('Email is required');
      return;
    }

    try {
      setLoading(true);
      
      // Only send fields that changed
      const updates: any = {};
      if (email !== user.email) updates.email = email;
      if (phone !== (user.phone || '')) updates.phone = phone || undefined;
      if (preference !== ((user as any).otpPreference || '')) updates.preference = preference || undefined;
      if (role !== user.role) updates.role = role;
      if (isActive !== user.isActive) updates.isActive = isActive;

      await onUpdate(user.id, updates);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setError(null);
    onClose();
  };

  if (!user) return null;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit User</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12}>
            <TextField
              fullWidth
              required
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={!!error && !email}
              disabled={loading}
            />
          </Grid>

          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Phone (optional)"
              placeholder="E.164 format: +15551234567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              disabled={loading}
            />
          </Grid>

          <Grid item xs={12}>
            <FormControl fullWidth disabled={loading}>
              <InputLabel>OTP Preference (optional)</InputLabel>
              <Select
                value={preference}
                label="OTP Preference (optional)"
                onChange={(e) => setPreference(e.target.value as any)}
              >
                <MenuItem value="">None</MenuItem>
                <MenuItem value="sms">SMS</MenuItem>
                <MenuItem value="email">Email</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <FormControl fullWidth required disabled={loading}>
              <InputLabel>Role</InputLabel>
              <Select
                value={role}
                label="Role"
                onChange={(e) => setRole(e.target.value as any)}
              >
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
                <MenuItem value="super-user">Super User</MenuItem>
              </Select>
            </FormControl>
          </Grid>

          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  disabled={loading}
                />
              }
              label="Account Active"
            />
          </Grid>

          {error && (
            <Grid item xs={12}>
              <div style={{ color: 'red', fontSize: '14px' }}>{error}</div>
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading || !email}
        >
          {loading ? 'Updating...' : 'Update User'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
