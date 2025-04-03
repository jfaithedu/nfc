import { useState, useEffect } from 'react';
import api from '../api/apiClient';

export function useAuth() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [expiresAt, setExpiresAt] = useState<number | null>(
    Number(localStorage.getItem('tokenExpiresAt')) || null
  );
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(!!token);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkTokenExpiration = () => {
      if (expiresAt && Date.now() >= expiresAt) {
        logout();
      }
    };

    checkTokenExpiration();
    const interval = setInterval(checkTokenExpiration, 60000); // Check every minute

    return () => clearInterval(interval);
  }, [expiresAt]);

  const login = async (pin: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.auth.login(pin);
      if (response.data.success) {
        const { token, expires_in } = response.data.data;
        const expiresAt = Date.now() + expires_in * 1000;
        
        localStorage.setItem('token', token);
        localStorage.setItem('tokenExpiresAt', String(expiresAt));
        
        setToken(token);
        setExpiresAt(expiresAt);
        setIsAuthenticated(true);
        
        return true;
      } else {
        setError('Login failed');
        return false;
      }
    } catch (err: any) {
      setError(err.response?.data?.error?.message || 'Login failed');
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('tokenExpiresAt');
    setToken(null);
    setExpiresAt(null);
    setIsAuthenticated(false);
  };

  return {
    token,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
  };
}

export default useAuth;