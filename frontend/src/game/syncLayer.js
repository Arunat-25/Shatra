/** @typedef {'synced' | 'pending' | 'desynced'} SyncStatus */
/** @typedef {'apply' | 'stale' | 'gap' | 'legacy'} PlyVerdict */

/**
 * Classify server move ply vs local confirmed ply.
 * @returns {PlyVerdict}
 */
export function classifyIncomingPly(confirmedPly, msgPly) {
  if (msgPly == null || msgPly === '') return 'legacy';
  const ply = Number(msgPly);
  const confirmed = Number(confirmedPly ?? 0);
  if (Number.isNaN(ply)) return 'legacy';
  if (ply <= confirmed) return 'stale';
  if (ply === confirmed + 1) return 'apply';
  return 'gap';
}

export function outstandingPlyCount(state) {
  if (state.pendingMoves?.length) return state.pendingMoves.length;
  return state.pendingMove ? 1 : 0;
}

export function nextOutgoingPly(state) {
  return Number(state.confirmedPly ?? 0) + outstandingPlyCount(state) + 1;
}

export function hasOutstandingPending(state) {
  return outstandingPlyCount(state) > 0;
}

/**
 * After server confirms ply, drop matching optimistic entry.
 */
export function pendingAfterConfirm(state, confirmedPly) {
  const pending = [...(state.pendingMoves || [])];
  if (!pending.length && state.pendingMove) {
    if (state.pendingMove.ply == null || state.pendingMove.ply === confirmedPly) {
      return { pendingMoves: [], pendingMove: null, rollbackSnapshot: null };
    }
    return {};
  }

  const rest = pending.filter((entry) => entry.ply !== confirmedPly);
  if (rest.length === pending.length) {
    return {};
  }

  return {
    pendingMoves: rest,
    pendingMove: rest[0] ?? null,
    rollbackSnapshot: rest.length ? state.rollbackSnapshot : null,
  };
}

export function isMoveConfirmation(data) {
  if (!data || data.game_over) return false;
  if (data.from_pos == null || data.to_pos == null) return false;
  return data.message_code != null || data.message;
}

/** Server payload confirming our optimistic WS send — client already reacted locally. */
export function isOwnOptimisticConfirmation(payload, state, myColor) {
  if (!hasOutstandingPending(state)) return false;

  const from = Number(payload?.from_pos ?? payload?.from);
  const to = Number(payload?.to_pos ?? payload?.to);
  const ply = payload?.ply != null ? Number(payload.ply) : null;

  const pending = state.pendingMoves?.length
    ? state.pendingMoves
    : state.pendingMove
      ? [state.pendingMove]
      : [];

  for (const entry of pending) {
    if (from > 0 && to > 0 && Number(entry.from) === from && Number(entry.to) === to) {
      return true;
    }
    if (ply != null && entry.ply != null && Number(entry.ply) === ply) {
      return true;
    }
  }

  if (!myColor) return false;
  const whoMoved = payload?.mover;
  return whoMoved === myColor;
}

/** Server game_over echo after optimistic move that already played endgame sound. */
export function isOptimisticGameEndEcho(payload, state) {
  if (!hasOutstandingPending(state)) return false;
  const from = Number(payload?.from_pos ?? payload?.from);
  const to = Number(payload?.to_pos ?? payload?.to);
  const ply = payload?.ply != null ? Number(payload.ply) : null;
  const pending = state.pendingMoves?.length
    ? state.pendingMoves
    : state.pendingMove
      ? [state.pendingMove]
      : [];
  return pending.some((entry) => {
    const cellsMatch = from > 0 && to > 0
      && Number(entry.from) === from && Number(entry.to) === to;
    const plyMatch = ply != null && entry.ply != null && Number(entry.ply) === ply;
    if (!cellsMatch && !plyMatch) return false;
    return entry.endsGame || Boolean(payload?.game_over);
  });
}

/** Rematch status echo after optimistic SET_REMATCH_STATUS or duplicate broadcast. */
export function isDuplicateRematchToast(data, state) {
  if (data?.status !== 'rematch_status') return false;
  if (data.self_ready && state.rematchReady) return true;
  if (data.opponent_ready && state.rematchOpponentReady && !data.self_ready) return true;
  return false;
}

/** game_cancelled echo after optimistic GAME_CANCELLED from cancelGame(). */
export function isDuplicateCancelConfirmation(state) {
  return Boolean(state.gameOver && state.gameOverReason === 'cancelled');
}
