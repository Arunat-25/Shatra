import { GAME_ACTIONS } from '../game/actions';
import { getClientId } from '../api';
import { getEffectiveVolume } from './soundSettings';
import { shouldSuppressActionSound } from '../game/serverFeedback';
import * as sounds from './gameSounds';

function vol() {
  return getEffectiveVolume();
}

function isDrawResult(payload) {
  const reason = payload?.reason || '';
  if (reason.includes('draw')) return true;
  const winner = payload?.winner_color || payload?.winner || '';
  return !winner;
}

export function playForAction(action, prevState, getMyColor) {
  if (vol() <= 0 || !action?.type) return;

  const myColor = getMyColor?.() ?? prevState?.myColor ?? null;
  if (shouldSuppressActionSound(action, prevState, myColor)) return;

  const v = vol();

  switch (action.type) {
    case GAME_ACTIONS.GAME_STARTED:
      sounds.playGameStart(v);
      break;

    case GAME_ACTIONS.MOVE_MADE: {
      const captured = action.payload?.captured_positions;
      if (Array.isArray(captured) && captured.length > 0) {
        sounds.playCapture(v);
      } else {
        sounds.playMove(v);
      }
      break;
    }

    case GAME_ACTIONS.OPTIMISTIC_MOVE: {
      const captured = action.payload?.result?.capturedPositions;
      if (Array.isArray(captured) && captured.length > 0) {
        sounds.playCapture(v);
      } else {
        sounds.playMove(v);
      }
      break;
    }

    case GAME_ACTIONS.GAME_OVER: {
      if (isDrawResult(action.payload)) {
        sounds.playDraw(v);
        break;
      }
      const winner = action.payload?.winner_color || action.payload?.winner || '';
      if (myColor && winner === myColor) {
        sounds.playWin(v);
      } else if (myColor && winner && winner !== myColor) {
        sounds.playLoss(v);
      } else {
        sounds.playDraw(v);
      }
      break;
    }

    case GAME_ACTIONS.GAME_CANCELLED:
      sounds.playDraw(v);
      break;

    case GAME_ACTIONS.CHAT_MESSAGE: {
      const from = action.payload?.client_id;
      if (from && from !== getClientId()) {
        sounds.playChat(v);
      }
      break;
    }

    case GAME_ACTIONS.SET_DRAW_OFFER: {
      const by = action.payload;
      if (by && myColor && by !== myColor) {
        sounds.playDrawOffer(v);
      }
      break;
    }

    default:
      break;
  }
}

export function playForServerError() {
  if (vol() <= 0) return;
  sounds.playError(vol());
}
