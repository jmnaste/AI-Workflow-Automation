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
  createdAt: string;
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
  // TODO: Replace with actual API call
  // const response = await fetch('/bff/auth/request-otp', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ email, phone, preference }),
  //   credentials: 'include',
  // });
  // if (!response.ok) throw new Error('Failed to request OTP');
  // return response.json();

  // Mock implementation
  console.log('Mock requestOtp:', { email, phone, preference });
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Simulate: 50% chance of new user
  const isNewUser = Math.random() > 0.5;
  
  return {
    success: true,
    isNewUser,
    message: isNewUser 
      ? 'Please complete your profile to receive OTP' 
      : 'OTP sent successfully',
  };
}

/**
 * Verify OTP and sign in
 */
export async function verifyOtp(email: string, otp: string): Promise<VerifyOtpResponse> {
  // TODO: Replace with actual API call
  // const response = await fetch('/bff/auth/verify-otp', {
  //   method: 'POST',
  //   headers: { 'Content-Type': 'application/json' },
  //   body: JSON.stringify({ email, otp }),
  //   credentials: 'include', // Include cookies
  // });
  // if (!response.ok) throw new Error('Invalid or expired OTP');
  // return response.json();

  // Mock implementation
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Simulate: Accept any 6-digit OTP for now
  if (otp.length !== 6) {
    throw new Error('Invalid OTP format');
  }
  
  return {
    success: true,
    user: {
      id: '1',
      email,
      phone: '+1234567890',
      otpPreference: 'sms',
      createdAt: new Date().toISOString(),
    },
  };
}

/**
 * Get current authenticated user
 */
export async function getCurrentUser(): Promise<UserProfile | null> {
  // TODO: Replace with actual API call
  // const response = await fetch('/bff/auth/me', {
  //   credentials: 'include', // Include cookies
  // });
  // if (response.status === 401) return null;
  // if (!response.ok) throw new Error('Failed to get user profile');
  // return response.json();

  // Mock implementation
  await new Promise(resolve => setTimeout(resolve, 200));
  return null; // Not authenticated
}

/**
 * Sign out current user
 */
export async function signOut(): Promise<void> {
  // TODO: Replace with actual API call
  // const response = await fetch('/bff/auth/logout', {
  //   method: 'POST',
  //   credentials: 'include',
  // });
  // if (!response.ok) throw new Error('Failed to sign out');

  // Mock implementation
  await new Promise(resolve => setTimeout(resolve, 200));
}
