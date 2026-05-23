import { COLOR_BLACK } from '../constants';
import { GAME_ACTIONS } from './actions';

export const messageHandlers = [
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
      return { text: `Игра окончена! Победил ${d.winner || 'ничья'}`, type: 'victory' };
    },
  },
  {
    check: (d) => d.message && d.desk,
    handle: (d, dispatch, modeAi) => {
      const aiThinking = modeAi && d.movers_color === COLOR_BLACK && !d.game_over;
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
    handle: (d, dispatch) => {
      if (d.move_history) {
        dispatch({ type: GAME_ACTIONS.SET_MOVE_HISTORY, payload: d.move_history });
      }
      dispatch({ type: GAME_ACTIONS.GAME_STARTED, payload: d });
      return { text: 'Игра началась!', type: 'info' };
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
];

export function dispatchServerMessage(data, dispatch, modeAi) {
  for (const { check, handle } of messageHandlers) {
    if (check(data)) {
      return handle(data, dispatch, modeAi);
    }
  }
  return null;
}
