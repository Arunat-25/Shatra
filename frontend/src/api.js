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

async function fetchWithTimeout(resource, options = {}) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
  try {
    return await fetch(resource, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function request(resource, options = {}) {
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await fetchWithTimeout(resource, options);
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new ApiError(err.detail || `Ошибка ${response.status}`, response.status);
      }
      return response.json();
    } catch (error) {
      if (attempt === MAX_RETRIES) {
        if (error instanceof ApiError) throw error;
        if (error.name === 'AbortError') throw new ApiError('Сервер не отвечает. Проверьте подключение к интернету.');
        throw new ApiError('Сервер недоступен. Попробуйте позже.');
      }
      if (error.name !== 'AbortError') {
        await new Promise(resolve => setTimeout(resolve, 500 * Math.pow(2, attempt)));
      }
    }
  }
}

export function createRoom(type = 'quick', timeControl = null, increment = null) {
  return request(`${API_BASE}/rooms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type, time_control: timeControl, increment }),
  });
}

export function listRooms() {
  return request(`${API_BASE}/rooms`);
}

export function joinRoom(roomId) {
  return request(`${API_BASE}/rooms/${roomId}/join`, { method: 'POST' });
}
