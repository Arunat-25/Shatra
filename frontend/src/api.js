const API_BASE = '';
const REQUEST_TIMEOUT = 10000;
const MAX_RETRIES = 2;

class ApiError extends Error {
  constructor(message, status = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(resource, options = {}) {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
    try {
      const response = await fetch(resource, { ...options, signal: controller.signal });
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new ApiError(err.detail || `Ошибка ${response.status}`, response.status);
      }
      return response.json();
    } catch (error) {
      clearTimeout(timeoutId);
      if (attempt === MAX_RETRIES) {
        if (error instanceof ApiError) throw error;
        if (error.name === 'AbortError') throw new ApiError('Сервер не отвечает. Проверьте подключение к интернету.');
        throw new ApiError('Сервер недоступен. Попробуйте позже.');
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
    headers: { 'Content-Type': 'application/json' },
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