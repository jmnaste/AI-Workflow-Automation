import { useState } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Alert,
  CircularProgress,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Stack,
} from '@mui/material';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useNavigate } from 'react-router-dom';
import { requestOtp, verifyOtp } from '../lib/api/auth.js';
import { setUser } from '../lib/auth.js';

// Validation schemas
const emailSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
});

const phoneSchema = z.object({
  phone: z.string().regex(/^\+?[1-9]\d{1,14}$/, 'Please enter a valid phone number (include country code)'),
  preference: z.enum(['sms', 'email'], { required_error: 'Please select OTP delivery method' }),
});

const otpSchema = z.object({
  otp: z.string().length(6, 'OTP must be 6 digits').regex(/^\d{6}$/, 'OTP must contain only numbers'),
});

type EmailForm = z.infer<typeof emailSchema>;
type PhoneForm = z.infer<typeof phoneSchema>;
type OtpForm = z.infer<typeof otpSchema>;

type Step = 'email' | 'phone' | 'otp';

export default function SignIn() {
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [isNewUser, setIsNewUser] = useState(false); // Will be used when API integration is complete
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const emailForm = useForm<EmailForm>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: '' },
  });

  const phoneForm = useForm<PhoneForm>({
    resolver: zodResolver(phoneSchema),
    defaultValues: { phone: '', preference: 'sms' },
  });

  const otpForm = useForm<OtpForm>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp: '' },
  });

  const handleEmailSubmit = async (data: EmailForm) => {
    setLoading(true);
    setError(null);
    try {
      const response = await requestOtp(data.email);
      
      setEmail(data.email);
      setIsNewUser(response.isNewUser);
      
      if (response.isNewUser) {
        setStep('phone');
      } else {
        // Existing user - OTP sent automatically
        setStep('otp');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process email');
    } finally {
      setLoading(false);
    }
  };

  const handlePhoneSubmit = async (data: PhoneForm) => {
    setLoading(true);
    setError(null);
    try {
      await requestOtp(email, data.phone, data.preference);
      setStep('otp');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleOtpSubmit = async (data: OtpForm) => {
    setLoading(true);
    setError(null);
    try {
      const response = await verifyOtp(email, data.otp);
      
      // Store user in auth state
      setUser(response.user);
      
      // On success, navigate to dashboard
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invalid or expired OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setLoading(true);
    setError(null);
    try {
      await requestOtp(email);
      // TODO: Show success toast instead of error state
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resend OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        backgroundColor: 'background.default',
        p: 2,
      }}
    >
      <Card sx={{ maxWidth: 440, width: '100%', p: 3, border: 1, borderColor: 'divider' }}>
        <CardContent>
          <Typography variant="h4" sx={{ mb: 1, fontWeight: 600, textAlign: 'center' }}>
            Sign In
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 4, textAlign: 'center', fontSize: '0.875rem' }}>
            {step === 'email' && 'Enter your email to continue'}
            {step === 'phone' && 'Complete your profile to receive OTP'}
            {step === 'otp' && `Enter the code sent to ${email}`}
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* Step 1: Email Entry */}
          {step === 'email' && (
            <form onSubmit={emailForm.handleSubmit(handleEmailSubmit)}>
              <TextField
                {...emailForm.register('email')}
                label="Email Address"
                type="email"
                fullWidth
                autoFocus
                error={!!emailForm.formState.errors.email}
                helperText={emailForm.formState.errors.email?.message}
                disabled={loading}
                sx={{ mb: 3 }}
              />
              <Button
                type="submit"
                variant="contained"
                fullWidth
                size="large"
                disabled={loading}
                startIcon={loading ? <CircularProgress size={20} /> : null}
              >
                {loading ? 'Processing...' : 'Continue'}
              </Button>
            </form>
          )}

          {/* Step 2: Phone & Preference (New Users Only) */}
          {step === 'phone' && (
            <form onSubmit={phoneForm.handleSubmit(handlePhoneSubmit)}>
              <Stack spacing={3}>
                <TextField
                  {...phoneForm.register('phone')}
                  label="Phone Number"
                  placeholder="+1234567890"
                  fullWidth
                  autoFocus
                  error={!!phoneForm.formState.errors.phone}
                  helperText={phoneForm.formState.errors.phone?.message || 'Include country code (e.g., +1 for US/Canada)'}
                  disabled={loading}
                />

                <FormControl component="fieldset" error={!!phoneForm.formState.errors.preference}>
                  <FormLabel component="legend">Receive OTP via:</FormLabel>
                  <RadioGroup defaultValue="sms" {...phoneForm.register('preference')}>
                    <FormControlLabel value="sms" control={<Radio />} label="SMS (Text Message)" />
                    <FormControlLabel value="email" control={<Radio />} label={`Email (${email})`} />
                  </RadioGroup>
                  {phoneForm.formState.errors.preference && (
                    <Typography variant="caption" color="error">
                      {phoneForm.formState.errors.preference.message}
                    </Typography>
                  )}
                </FormControl>

                <Button
                  type="submit"
                  variant="contained"
                  fullWidth
                  size="large"
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : null}
                >
                  {loading ? 'Sending OTP...' : 'Send OTP'}
                </Button>

                <Button
                  variant="text"
                  fullWidth
                  onClick={() => setStep('email')}
                  disabled={loading}
                >
                  Back
                </Button>
              </Stack>
            </form>
          )}

          {/* Step 3: OTP Entry */}
          {step === 'otp' && (
            <form onSubmit={otpForm.handleSubmit(handleOtpSubmit)}>
              <Stack spacing={3}>
                <TextField
                  {...otpForm.register('otp')}
                  label="6-Digit Code"
                  placeholder="000000"
                  fullWidth
                  autoFocus
                  inputProps={{ maxLength: 6, style: { textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.5rem' } }}
                  error={!!otpForm.formState.errors.otp}
                  helperText={otpForm.formState.errors.otp?.message}
                  disabled={loading}
                />

                <Button
                  type="submit"
                  variant="contained"
                  fullWidth
                  size="large"
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={20} /> : null}
                >
                  {loading ? 'Verifying...' : 'Verify & Sign In'}
                </Button>

                <Button
                  variant="text"
                  fullWidth
                  onClick={handleResendOtp}
                  disabled={loading}
                >
                  Resend Code
                </Button>

                <Button
                  variant="text"
                  fullWidth
                  onClick={() => {
                    setStep('email');
                    setEmail('');
                    emailForm.reset();
                    phoneForm.reset();
                    otpForm.reset();
                  }}
                  disabled={loading}
                  sx={{ fontSize: '0.875rem' }}
                >
                  Use Different Email
                </Button>
              </Stack>
            </form>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
