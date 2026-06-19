import { applyMoveDelta } from '../ws/v2/applyDelta.js';

export { applyMoveDelta } from '../ws/v2/applyDelta.js';

/**
 * Resolve board after a server move payload (full desk or delta-only).
 */
export function resolveBoardFromPayload(currentBoard, payload) {
  if (payload?.desk) {
    const out = {};
    for (const [k, v] of Object.entries(payload.desk)) {
      out[Number(k)] = v ?? null;
    }
    return out;
  }

  const from = payload?.from_pos;
  const to = payload?.to_pos;
  if (from == null || to == null) {
    return currentBoard || {};
  }
  const f = Number(from);
  const t = Number(to);
  if (f === 0 && t === 0) {
    return currentBoard || {};
  }

  return applyMoveDelta(currentBoard || {}, {
    from,
    to,
    captured: payload.captured_positions || [],
    promoted: Boolean(payload.promoted),
  });
}

export function appendLocalMoveHistory(history, board, payload) {
  const from = payload?.from_pos;
  const to = payload?.to_pos;
  if (from == null || to == null) return history || [];
  const f = Number(from);
  const t = Number(to);
  if (!f && !t) return history || [];

  const desk = {};
  for (const [k, v] of Object.entries(board || {})) {
    desk[String(k)] = v ?? null;
  }

  const entry = {
    move_number: (history?.length || 0) + 1,
    mover: payload.mover,
    from_pos: f,
    to_pos: t,
    desk,
  };
  if (payload.captured_positions?.length) {
    entry.captured_positions = payload.captured_positions;
  }
  return [...(history || []), entry];
}
