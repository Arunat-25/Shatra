import { getAccessToken } from './api/auth';
import i18n from './i18n';
import { ApiError } from './api/errors';

export { ApiError };

const API_BASE = '';
const REQUEST_TIMEOUT = 10000;
const MAX_RETRIES = 2;

function authHeaders(extra = {}) {
  const headers = { ...extra };
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

async function request(resource, options = {}) {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    const headers = authHeaders(options.headers);
    if (options.body && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }
    try {
      const response = await fetch(resource, {
        ...options,
        headers,
        signal: controller.signal,
      });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new ApiError(
          err.detail || i18n.t('errors.genericHttp', { status: response.status }),
          response.status,
        );
      }
      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (attempt === MAX_RETRIES) {
        if (error instanceof ApiError) throw error;
        if (error.name === 'AbortError') throw new ApiError(i18n.t('errors.serverNoResponse'));
        throw new ApiError(i18n.t('errors.serverUnavailable'));
      }
      if (error.name !== 'AbortError') {
        await new Promise(resolve => setTimeout(resolve, 500 * Math.pow(2, attempt)));
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }
}

// ===== Идентификация игрока =====

const CLIENT_ID_KEY = 'shatra_client_id';

export function getClientId() {
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
}

export function getWsUrl(roomId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/${roomId}/?client_id=${getClientId()}`;
}

// ===== REST API =====

export function createRoom(
  type = 'public',
  timeControl = null,
  increment = null,
  colorPreference = 'random',
) {
  return request(`${API_BASE}/rooms`, {
    method: 'POST',
    body: JSON.stringify({
      type,
      time_control: timeControl,
      increment,
      color_preference: colorPreference,
      creator_client_id: getClientId(),
    }),
  });
}

export function listRooms() {
  return request(`${API_BASE}/rooms`);
}

export function joinRoom(roomId) {
  return request(`${API_BASE}/rooms/${roomId}/join`, { method: 'POST' });
}
