import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { authService } from '../services/authService';
import { Organization, RegisterRequest, User } from '../types/auth';

interface AuthContextType {
  user: User | null;
  organization: Organization | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchUser = async () => {
    const token = localStorage.getItem('askdesk_access_token');
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const currentUser = await authService.getCurrentUser();
      setUser(currentUser);
    } catch {
      localStorage.removeItem('askdesk_access_token');
      localStorage.removeItem('askdesk_refresh_token');
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const saveSession = (response: { access?: string; refresh?: string; tokens?: { access: string; refresh: string }; user: User }) => {
    const accessToken = response.access || response.tokens?.access;
    const refreshToken = response.refresh || response.tokens?.refresh;
    if (accessToken) {
      localStorage.setItem('askdesk_access_token', accessToken);
    }
    if (refreshToken) {
      localStorage.setItem('askdesk_refresh_token', refreshToken);
    }
    setUser(response.user);
  };

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    try {
      const response = await authService.login(email, pass);
      saveSession(response);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: RegisterRequest) => {
    setIsLoading(true);
    try {
      const response = await authService.register(data);
      saveSession(response);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('askdesk_access_token');
    localStorage.removeItem('askdesk_refresh_token');
    setUser(null);
    window.location.href = '/login';
  };

  const refreshUser = async () => {
    await fetchUser();
  };

  const value: AuthContextType = {
    user,
    organization: user?.organization || null,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'ADMIN',
    isLoading,
    login,
    register,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
