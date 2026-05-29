import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY } from '../constants/profile';
import i18n from '../i18n';

const API_BASE = '';

class ApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function getStoredTokens() {
  return {
    access: localStorage.getItem(ACCESS_TOKEN_KEY),
    refresh: localStorage.getItem(REFRESH_TOKEN_KEY),
  };
}

export function setTokens(access, refresh, onRefreshed) {
  localStorage.setItem(ACCESS_TOKEN_KEY, access);
  localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
  scheduleTokenRefresh(onRefreshed);
}

let refreshTimer = null;

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  clearScheduledTokenRefresh();
}

export function decodeAccessExp(token) {
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const padded = part.replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(padded));
    return typeof payload.exp === 'number' ? payload.exp : null;
  } catch {
    return null;
  }
}

export function clearScheduledTokenRefresh() {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
}

/** Задержка (мс) до проактивного refresh: за 2 мин до exp, минимум 5 с. */
export function computeRefreshDelayMs(expSeconds, nowMs = Date.now()) {
  const refreshAt = expSeconds * 1000 - nowMs - 2 * 60 * 1000;
  return Math.max(refreshAt, 5000);
}

/** Планирует refresh за ~2 мин до истечения access token. */
export function scheduleTokenRefresh(onRefreshed) {
  clearScheduledTokenRefresh();
  const access = getAccessToken();
  if (!access) return;

  const exp = decodeAccessExp(access);
  if (!exp) return;

  const delay = computeRefreshDelayMs(exp);

  refreshTimer = setTimeout(async () => {
    const { refresh } = getStoredTokens();
    if (!refresh) return;
    try {
      const response = await fetch(`${API_BASE}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) {
        clearTokens();
        return;
      }
      const data = await response.json();
      setTokens(data.access_token, data.refresh_token);
      onRefreshed?.(data);
      scheduleTokenRefresh(onRefreshed);
    } catch {
      // fallback: authFetch on next 401
    }
  }, delay);
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

async function parseError(response) {
  const err = await response.json().catch(() => ({}));
  const detail = err.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg || d.message || String(d)).join('. ');
  }
  return i18n.t('errors.genericHttp', { status: response.status });
}

async function authFetch(path, options = {}, retry = true) {
  const { access, refresh } = getStoredTokens();
  const headers = { ...options.headers };
  if (access) headers.Authorization = `Bearer ${access}`;
  if (options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (response.status === 401 && retry && refresh) {
    const refreshed = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (refreshed.ok) {
      const data = await refreshed.json();
      setTokens(data.access_token, data.refresh_token);
      return authFetch(path, options, false);
    }
    clearTokens();
  }

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function register(payload) {
  return authFetch('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(payload),
  }, false);
}

export function login(username, password) {
  return authFetch('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  }, false);
}

export function logout() {
  const { refresh } = getStoredTokens();
  if (refresh) {
    return authFetch('/api/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refresh }),
    }, false).finally(clearTokens);
  }
  clearTokens();
  return Promise.resolve();
}

export function fetchMe() {
  return authFetch('/api/auth/me');
}

export function updateProfile(payload) {
  return authFetch('/api/auth/me', {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export function changePassword(currentPassword, newPassword) {
  return authFetch('/api/auth/password/change', {
    method: 'POST',
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

export { ApiError };
