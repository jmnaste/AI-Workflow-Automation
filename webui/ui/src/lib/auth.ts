// Auth state management for OTP-based passwordless authentication
import { UserProfile, getCurrentUser, signOut as apiSignOut } from './api/auth.js';

export interface AuthSession {
  user: UserProfile | null;
  isAuthenticated: boolean;
}

let current: AuthSession = {
  user: null,
  isAuthenticated: false,
};

/**
 * Get current auth session
 */
export function getSession(): AuthSession {
  return current;
}

/**
 * Set user profile after successful authentication
 */
export function setUser(user: UserProfile | null) {
  current = {
    user,
    isAuthenticated: !!user,
  };
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated(): boolean {
  return current.isAuthenticated && !!current.user;
}

/**
 * Initialize auth state (call on app load)
 * Fetches current user from BFF to restore session
 */
export async function initAuth(): Promise<void> {
  try {
    const user = await getCurrentUser();
    setUser(user);
  } catch (error) {
    console.error('Failed to initialize auth:', error);
    setUser(null);
  }
}

/**
 * Sign out current user
 */
export async function signOut(): Promise<void> {
  try {
    await apiSignOut();
  } finally {
    setUser(null);
  }
}
