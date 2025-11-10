import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { UserProfile, getCurrentUser } from '../lib/api/auth.js';

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: UserProfile | null) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state on mount
  useEffect(() => {
    getCurrentUser()
      .then(setUserState)
      .catch(() => setUserState(null))
      .finally(() => setIsLoading(false));
  }, []);

  const setUser = (newUser: UserProfile | null) => {
    setUserState(newUser);
  };

  const signOut = () => {
    setUserState(null);
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    setUser,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
