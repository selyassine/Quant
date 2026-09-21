'use client';
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

interface User {
  email: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check for stored auth on mount
    const storedAuth = localStorage.getItem('quantai_auth');
    if (storedAuth) {
      try {
        const auth = JSON.parse(storedAuth);
        setUser(auth.user);
        setIsAuthenticated(true);
      } catch (e) {
        localStorage.removeItem('quantai_auth');
      }
    }
  }, []);

  const login = async (email: string, password: string) => {
    // Simulate API call - replace with actual authentication
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Demo: accept any email/password for now
    const user: User = {
      email,
      name: email.split('@')[0]
    };
    
    setUser(user);
    setIsAuthenticated(true);
    localStorage.setItem('quantai_auth', JSON.stringify({ user }));
  };

  const logout = () => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('quantai_auth');
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
