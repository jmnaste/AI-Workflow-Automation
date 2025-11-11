// Auth API Client
// TODO: Replace mock implementations with actual BFF calls

export interface RequestOtpRequest {
  email: string;
  phone?: string;
  preference?: 'sms' | 'email';
}

export interface RequestOtpResponse {
  success: boolean;
  isNewUser: boolean;
  message: string;
}

export interface VerifyOtpRequest {
  email: string;
  otp: string;
}

export interface UserProfile {
  id: string;
  email: string;
  phone: string;
  otpPreference: 'sms' | 'email';
  role: 'user' | 'admin' | 'super';
  isActive: boolean;
  verifiedAt: string | null;
  createdAt: string;
  lastLoginAt: string | null;
}

export interface VerifyOtpResponse {
  success: boolean;
  user: UserProfile;
}

/**
 * Request OTP for email (and optionally register new user with phone)
 */
export async function requestOtp(
  email: string,
  phone?: string,
  preference?: 'sms' | 'email'
): Promise<RequestOtpResponse> {
  const response = await fetch('/bff/auth/request-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, phone, preference }),
    credentials: 'include',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to request OTP');
  }
  return response.json();
}

/**
 * Verify OTP and sign in
 */
export async function verifyOtp(email: string, otp: string): Promise<VerifyOtpResponse> {
  const response = await fetch('/bff/auth/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, otp }),
    credentials: 'include', // Include cookies
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Invalid or expired OTP');
  }
  return response.json();
}

/**
 * Get current authenticated user
 */
export async function getCurrentUser(): Promise<UserProfile | null> {
  const response = await fetch('/bff/auth/me', {
    credentials: 'include', // Include cookies
  });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error('Failed to get user profile');
  return response.json();
}

/**
 * Sign out current user
 */
export async function signOut(): Promise<void> {
  const response = await fetch('/bff/auth/logout', {
    method: 'POST',
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Failed to sign out');
}
