export const RECONNECT_BASE_DELAY_MS = 500;
export const RECONNECT_MAX_DELAY_MS = 5000;
export const MAX_RECONNECT_ATTEMPTS = 12;

export const FATAL_CLOSE_RULES = [
  { match: 'комната уже заполнена', type: 'room_full', message: 'Комната уже заполнена' },
  { match: 'вы уже в игре', type: 'already_in_game', message: 'Игра уже открыта в другой вкладке' },
  { match: 'комната не найдена', type: 'room_not_found', message: 'Комната не найдена' },
];

export function getReconnectDelay(attempt) {
  const delay = RECONNECT_BASE_DELAY_MS * 2 ** (attempt - 1);
  return Math.min(delay, RECONNECT_MAX_DELAY_MS);
}

export function classifyClose(event) {
  const reason = (event.reason || '').toLowerCase();

  if (event.code === 1000) {
    return { recoverable: false, type: 'normal' };
  }

  for (const rule of FATAL_CLOSE_RULES) {
    if (reason.includes(rule.match)) {
      return {
        recoverable: false,
        type: rule.type,
        message: event.reason || rule.message,
      };
    }
  }

  return {
    recoverable: true,
    type: 'transient',
    message: event.reason || 'Потеряно соединение. Пытаюсь восстановить...',
  };
}

export function parseWsMessage(raw) {
  try {
    const data = JSON.parse(raw);
    if (data == null || typeof data !== 'object' || Array.isArray(data)) {
      return {
        ok: false,
        error: {
          type: 'malformed',
          recoverable: true,
          message: 'Получено некорректное сообщение от сервера',
        },
      };
    }
    return { ok: true, data };
  } catch {
    return {
      ok: false,
      error: {
        type: 'malformed',
        recoverable: true,
        message: 'Не удалось разобрать ответ сервера',
      },
    };
  }
}

export function shouldStopReconnecting(attempt) {
  return attempt > MAX_RECONNECT_ATTEMPTS;
}
