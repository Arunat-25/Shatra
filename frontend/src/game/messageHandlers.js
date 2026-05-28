import { GAME_ACTIONS } from './actions';

function isAiThinking(modeAi, moversColor, myColor, payload) {
  if (!modeAi || !myColor || payload.game_over) return false;
  if (payload.position_for_mandatory_capture) return false;
  return moversColor !== myColor;
}

export const messageHandlers = [
  {
    check: (d) => d.status === 'error',
    handle: (d) => ({ text: d.message || 'Ошибка сервера', type: 'error' }),
  },
  {
    check: (d) => d.status === 'waiting',
    handle: (_d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.SET_WAITING });
      return null;
    },
  },
  {
    check: (d) => d.game_over,
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.GAME_OVER, payload: d });
      return null;
    },
  },
  {
    check: (d) => d.message && d.desk,
    handle: (d, dispatch, modeAi, getMyColor) => {
      const myColor = getMyColor?.() || null;
      const aiThinking = isAiThinking(modeAi, d.movers_color, myColor, d);
      if (d.move_history) {
        dispatch({ type: GAME_ACTIONS.SET_MOVE_HISTORY, payload: d.move_history });
      }
      dispatch({ type: GAME_ACTIONS.MOVE_MADE, payload: { ...d, aiThinking } });
      return { text: d.message, type: 'info' };
    },
  },
  {
    check: (d) => d.essential_positions !== undefined && !d.message,
    handle: (d, dispatch) => {
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
      const myColor = getMyColor?.() || d.your_color || null;
      const aiThinking = isAiThinking(modeAi, d.movers_color, myColor, d);
      if (d.move_history) {
        dispatch({ type: GAME_ACTIONS.SET_MOVE_HISTORY, payload: d.move_history });
      }
      dispatch({ type: GAME_ACTIONS.GAME_STARTED, payload: { ...d, aiThinking } });
      return { text: 'Игра началась!', type: 'info' };
    },
  },
  {
    check: (d) => d.status === 'draw_offered',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.SET_DRAW_OFFER, payload: d.by || null });
      return { text: d.message || 'Предложение ничьей', type: 'info' };
    },
  },
  {
    check: (d) => d.status === 'draw_declined',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.SET_DRAW_OFFER, payload: null });
      return { text: d.message || 'Предложение ничьей отклонено.', type: 'warning' };
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
      if (d.self_ready) {
        return { text: 'Ожидание согласия соперника на реванш…', type: 'info' };
      }
      if (d.opponent_ready) {
        return { text: 'Соперник готов к реваншу. Нажмите «Реванш».', type: 'info' };
      }
      return null;
    },
  },
  {
    check: (d) => d.status === 'rematch_cancelled',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.SET_REMATCH_UNAVAILABLE });
      return { text: d.message || 'Реванш отменён.', type: 'warning' };
    },
  },
  {
    check: (d) => d.status === 'opponent_disconnected',
    handle: (d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.OPPONENT_DISCONNECTED, payload: d });
      return { text: 'Соперник отключился. Ожидание переподключения...', type: 'warning' };
    },
  },
  {
    check: (d) => d.status === 'opponent_reconnected',
    handle: (_d, dispatch) => {
      dispatch({ type: GAME_ACTIONS.OPPONENT_RECONNECTED });
      return { text: 'Соперник вернулся! Игра продолжается.', type: 'info' };
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
