import { GAME_ACTIONS } from '../game/actions';
import { getClientId } from '../api';
import { getEffectiveVolume } from './soundSettings';
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

function isRealMove(payload) {
  const from = payload?.from_pos;
  const to = payload?.to_pos;
  if (from == null || to == null) return false;
  const f = Number(from);
  const t = Number(to);
  return f > 0 && t > 0 && f !== t;
}

export function playForAction(action, prevState, getMyColor) {
  if (vol() <= 0 || !action?.type) return;

  const myColor = getMyColor?.() ?? prevState?.myColor ?? null;
  const v = vol();

  switch (action.type) {
    case GAME_ACTIONS.GAME_STARTED:
      sounds.playGameStart(v);
      break;

    case GAME_ACTIONS.MOVE_MADE: {
      if (!isRealMove(action.payload)) break;
      const captured = action.payload?.captured_positions;
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
