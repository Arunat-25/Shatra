import { GAME_ACTIONS } from './actions';
import i18n from '../i18n';
import { resolveMessage } from '../i18n/resolveMessage';
import { trackGameEvent } from '../observability/events';

function t(key, opts) {
  return i18n.t(key, opts);
}

function msg(payload, type) {
  return { text: resolveMessage(payload) || t('server.error'), type };
}

function isAiThinking(modeAi, moversColor, myColor, payload) {
  if (!modeAi || !myColor || payload.game_over) return false;
  if (payload.position_for_mandatory_capture) return false;
  return moversColor !== myColor;
}

export const messageHandlers = [
  {
    check: (d) => d.status === 'error',
    handle: (d) => msg(d, 'error'),
  },
  {
    check: (d) => d.status === 'waiting',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.SET_WAITING });
      dispatch({
        type: GAME_ACTIONS.SET_WAITING_META,
        payload: {
          roomType: d.room_type ?? null,
          showInviteLink: Boolean(d.show_invite_link),
        },
      });
      if (d.players_info) {
        dispatch({ type: GAME_ACTIONS.SET_PLAYERS_INFO, payload: d.players_info });
      }
      return null;
    },
  },
  {
    check: (d) => d.type === 'chat_history',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.CHAT_HISTORY, payload: d.messages || [] });
      return null;
    },
  },
  {
    check: (d) => d.type === 'chat',
    handle: (d, dispatch) => {
      dispatch({
        type: GAME_ACTIONS.CHAT_MESSAGE,
        payload: {
          client_id: d.from_client_id,
          username: d.username,
          text: d.text,
          ts: d.ts,
          is_anonymous: d.is_anonymous,
          display_name: d.display_name,
        },
      });
      return null;
    },
  },
  {
    check: (d) => d.game_over,
    handle: (d, dispatch) => {
      trackGameEvent('game_over', {
        reason: d.reason,
        winnerColor: d.winner_color,
      });
      dispatch({ type: GAME_ACTIONS.GAME_OVER, payload: d });
      return null;
    },
  },
  {
    check: (d) => d.desk && (d.message_code != null || d.message),
    handle: (d, dispatch, modeAi, getMyColor) => {
      const myColor = getMyColor?.() || null;
      const aiThinking = isAiThinking(modeAi, d.movers_color, myColor, d);
      if (d.move_history) {
        dispatch({ type: GAME_ACTIONS.SET_MOVE_HISTORY, payload: d.move_history });
      }
      dispatch({ type: GAME_ACTIONS.MOVE_MADE, payload: { ...d, aiThinking } });
      if (d.essential_positions?.length && d.movers_color === myColor) {
        dispatch({
          type: GAME_ACTIONS.HIGHLIGHTS,
          payload: {
            essential: d.essential_positions || [],
            captured: d.captured_pieces || [],
          },
        });
      }
      if (d.game_over) return null;
      return msg(d, 'info');
    },
  },
  {
    check: (d) => d.essential_positions !== undefined && !d.message_code && !d.message,
    handle: (d, dispatch, _modeAi, getMyColor) => {
      const myColor = getMyColor?.() || null;
      if (d.movers_color != null && d.movers_color !== myColor) return null;
      dispatch({
        type: GAME_ACTIONS.HIGHLIGHTS,
        payload: {
          essential: d.essential_positions || [],
          captured: d.captured_pieces || [],
        },
      });
      return null;
    },
  },
  {
    check: (d) => d.status === 'game_started' && d.desk,
    handle: (d, dispatch, modeAi, getMyColor) => {
      if (d.players_info) {
        dispatch({ type: GAME_ACTIONS.SET_PLAYERS_INFO, payload: d.players_info });
      }
      const myColor = getMyColor?.() || d.your_color || null;
      const aiThinking = isAiThinking(modeAi, d.movers_color, myColor, d);
      if (d.move_history) {
        dispatch({ type: GAME_ACTIONS.SET_MOVE_HISTORY, payload: d.move_history });
      }
      trackGameEvent('game_started', { modeAi, moversColor: d.movers_color });
      dispatch({ type: GAME_ACTIONS.GAME_STARTED, payload: { ...d, aiThinking } });
      return { text: t('game.gameStarted'), type: 'info' };
    },
  },
  {
    check: (d) => d.status === 'draw_offered',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.SET_DRAW_OFFER, payload: d.by || null });
      return d.message_code
        ? msg(d, 'info')
        : { text: t('server.drawOffer'), type: 'info' };
    },
  },
  {
    check: (d) => d.status === 'draw_declined',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.SET_DRAW_OFFER, payload: null });
      return d.message_code
        ? msg(d, 'warning')
        : { text: t('server.drawDeclined'), type: 'warning' };
    },
  },
  {
    check: (d) => d.status === 'game_cancelled',
    handle: (d, dispatch) => {
      dispatch({
        type: GAME_ACTIONS.GAME_CANCELLED,
        payload: {
          message_code: d.message_code || 'cancel.opponent',
          message_params: d.message_params,
        },
      });
      return null;
    },
  },
  {
    check: (d) => d.status === 'rematch_status',
    handle: (d, dispatch) => {
      dispatch({
        type: GAME_ACTIONS.SET_REMATCH_STATUS,
        payload: { self_ready: d.self_ready, opponent_ready: d.opponent_ready },
      });
      if (d.self_ready && d.opponent_ready) return null;
      if (d.self_ready) return { text: t('server.rematchWaitSelf'), type: 'info' };
      if (d.opponent_ready) return { text: t('server.rematchWaitOpponent'), type: 'info' };
      return null;
    },
  },
  {
    check: (d) => d.status === 'rematch_cancelled',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.SET_REMATCH_UNAVAILABLE });
      return d.message_code
        ? msg(d, 'warning')
        : { text: t('server.rematchCancelled'), type: 'warning' };
    },
  },
  {
    check: (d) => d.status === 'opponent_disconnected',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.OPPONENT_DISCONNECTED, payload: d });
      return null;
    },
  },
  {
    check: (d) => d.status === 'opponent_reconnected',
    handle: (_d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.OPPONENT_RECONNECTED });
      return { text: t('disconnect.reconnected'), type: 'info' };
    },
  },
  {
    check: (d) => d.type === 'timer_tick',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.TIMER_TICK, payload: d.time });
      return null;
    },
  },
  {
    check: (d) => d.type === 'disconnect_tick',
    handle: (d, dispatch) => {
      if (typeof d.remaining === 'number') {
        dispatch({ type: GAME_ACTIONS.SET_DISCONNECT_COUNTDOWN, payload: d.remaining });
      }
      return null;
    },
  },
];

export function dispatchServerMessage(data, dispatch, modeAi, getMyColor) {
  for (const { check, handle } of messageHandlers) {
    if (check(data)) {
      return handle(data, dispatch, modeAi, getMyColor);
    }
  }
  if (import.meta.env?.DEV) {
    console.warn('[ws] unhandled server message', data);
  }
  return null;
}
