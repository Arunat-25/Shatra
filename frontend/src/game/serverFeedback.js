import { GAME_ACTIONS } from './actions';
import {
  isMoveConfirmation,
  isOwnOptimisticConfirmation,
  isDuplicateRematchToast,
  isDuplicateCancelConfirmation,
} from './syncLayer';

/**
 * Scenarios where client reacts optimistically and server echo must not duplicate UX.
 * Used as living documentation + test matrix.
 */
export const FEEDBACK_SCENARIOS = [
  {
    id: 'move_confirm',
    suppressToast: true,
    suppressSound: true,
    when: 'Server confirms our optimistic move (MOVE_MADE)',
  },
  {
    id: 'resync_snapshot',
    suppressToast: true,
    suppressSound: true,
    when: 'Reconnect/reject sync snapshot (_resync GAME_STARTED)',
  },
  {
    id: 'rematch_status_echo',
    suppressToast: true,
    suppressSound: false,
    when: 'rematch_status after optimistic SET_REMATCH_STATUS',
  },
  {
    id: 'cancel_echo',
    suppressToast: false,
    suppressSound: true,
    when: 'game_cancelled after optimistic GAME_CANCELLED',
  },
];

function isRealMove(payload) {
  const from = payload?.from_pos;
  const to = payload?.to_pos;
  if (from == null || to == null) return false;
  const f = Number(from);
  const t = Number(to);
  return f > 0 && t > 0 && f !== t;
}

/** Suppress server toast when client already showed the same feedback. */
export function shouldSuppressServerToast(data, state, myColor) {
  if (!data) return false;
  if (isMoveConfirmation(data) && isOwnOptimisticConfirmation(data, state, myColor)) {
    return true;
  }
  if (isDuplicateRematchToast(data, state)) {
    return true;
  }
  return false;
}

/** Suppress action sound when state already reflects the same event. */
export function shouldSuppressActionSound(action, prevState, myColor) {
  if (!action?.type) return true;

  switch (action.type) {
    case GAME_ACTIONS.GAME_STARTED:
      return Boolean(action.payload?._resync);
    case GAME_ACTIONS.MOVE_MADE:
      if (!isRealMove(action.payload)) return true;
      return isOwnOptimisticConfirmation(action.payload, prevState, myColor);
    case GAME_ACTIONS.GAME_CANCELLED:
      return isDuplicateCancelConfirmation(prevState);
    default:
      return false;
  }
}
