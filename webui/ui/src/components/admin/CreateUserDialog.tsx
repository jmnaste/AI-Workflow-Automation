import { useState } from 'react';
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
} from '@mui/material';

/**
 * User Role Definitions:
 * - user: Standard user with basic access
 * - super: Elevated user with additional business workflow privileges (NO admin console access)
 * - admin: Full administrative access including admin console and user management
 * 
 * Note: Only 'admin' role can access admin console.
 */
interface CreateUserDialogProps {
  open: boolean;
  onClose: () => void;
  onCreate: (userData: {
    email: string;
    phone?: string;
    preference?: 'sms' | 'email';
    role: 'user' | 'admin' | 'super';
  }) => Promise<void>;
}

export default function CreateUserDialog({ open, onClose, onCreate }: CreateUserDialogProps) {
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [preference, setPreference] = useState<'sms' | 'email' | ''>('');
  const [role, setRole] = useState<'user' | 'admin' | 'super'>('user');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    setError(null);
    
    // Validation
    if (!email) {
      setError('Email is required');
      return;
    }

    try {
      setLoading(true);
      await onCreate({
        email,
        phone: phone || undefined,
        preference: preference || undefined,
        role,
      });
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setEmail('');
    setPhone('');
    setPreference('');
    setRole('user');
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Create New User</DialogTitle>
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
              helperText={!email && error ? 'Email is required' : ''}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              fullWidth
              label="Phone Number"
              placeholder="+1234567890"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              helperText="Optional: E.164 format with country code"
            />
          </Grid>
          <Grid item xs={12}>
            <FormControl fullWidth>
              <InputLabel>OTP Preference</InputLabel>
              <Select
                value={preference}
                label="OTP Preference"
                onChange={(e) => setPreference(e.target.value as 'sms' | 'email' | '')}
              >
                <MenuItem value="">None (user chooses on first login)</MenuItem>
                <MenuItem value="sms">SMS</MenuItem>
                <MenuItem value="email">Email</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12}>
            <FormControl fullWidth required>
              <InputLabel>Role</InputLabel>
              <Select
                value={role}
                label="Role"
                onChange={(e) => setRole(e.target.value as 'user' | 'admin' | 'super')}
              >
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
                <MenuItem value="super">Super Admin</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          {error && (
            <Grid item xs={12}>
              <TextField
                fullWidth
                error
                value={error}
                InputProps={{ readOnly: true }}
                variant="outlined"
                multiline
              />
            </Grid>
          )}
        </Grid>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button onClick={handleSubmit} variant="contained" disabled={loading}>
          {loading ? 'Creating...' : 'Create User'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
