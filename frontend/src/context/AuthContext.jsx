import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import {
  clearTokens,
  fetchMe,
  getAccessToken,
  login as apiLogin,
  logout as apiLogout,
  scheduleTokenRefresh,
  setTokens,
} from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const onTokensRefreshed = useCallback((data) => {
    if (data?.user) setUser(data.user);
  }, []);

  const loadUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await fetchMe();
      setUser(me);
      scheduleTokenRefresh(onTokensRefreshed);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, [onTokensRefreshed]);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  const login = useCallback(async (username, password) => {
    const data = await apiLogin(username, password);
    setTokens(data.access_token, data.refresh_token, onTokensRefreshed);
    setUser(data.user);
    return data.user;
  }, [onTokensRefreshed]);

  const applyTokens = useCallback((data) => {
    setTokens(data.access_token, data.refresh_token, onTokensRefreshed);
    setUser(data.user);
  }, [onTokensRefreshed]);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      applyTokens,
      logout,
      refreshUser: loadUser,
      setUser,
    }),
    [user, loading, login, applyTokens, logout, loadUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
