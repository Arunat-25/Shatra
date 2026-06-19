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
