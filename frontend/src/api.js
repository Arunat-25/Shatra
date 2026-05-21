const API_BASE = '';

export async function createRoom(type = 'quick') {
  const res = await fetch(`${API_BASE}/rooms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ type }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Ошибка создания комнаты');
  }
  return res.json();
}

export async function listRooms() {
  const res = await fetch(`${API_BASE}/rooms`);
  if (!res.ok) throw new Error('Ошибка загрузки');
  return res.json();
}

export async function joinRoom(roomId) {
  const res = await fetch(`${API_BASE}/rooms/${roomId}/join`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Ошибка присоединения');
  }
  return res.json();
}

