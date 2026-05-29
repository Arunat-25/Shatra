export const RECONNECT_BASE_DELAY_MS = 500;
export const RECONNECT_MAX_DELAY_MS = 5000;
export const MAX_RECONNECT_ATTEMPTS = 12;

export const FATAL_CLOSE_RULES = [
  { code: 'room_full', type: 'room_full' },
  { code: 'already_in_game', type: 'already_in_game' },
  { code: 'room_not_found', type: 'room_not_found' },
];

export function getReconnectDelay(attempt) {
  const delay = RECONNECT_BASE_DELAY_MS * 2 ** (attempt - 1);
  return Math.min(delay, RECONNECT_MAX_DELAY_MS);
}

export function classifyClose(event) {
  const reason = (event.reason || '').trim().toLowerCase();

  if (event.code === 1000) {
    return { recoverable: false, type: 'normal' };
  }

  for (const rule of FATAL_CLOSE_RULES) {
    if (reason === rule.code) {
      return {
        recoverable: false,
        type: rule.type,
        message: event.reason || rule.code,
      };
    }
  }

  return {
    recoverable: true,
    type: 'transient',
    message: event.reason || 'connection_lost',
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
          message: 'ws.expected_object',
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
        message: 'ws.invalid_json',
      },
    };
  }
}

export function shouldStopReconnecting(attempt) {
  return attempt > MAX_RECONNECT_ATTEMPTS;
}
