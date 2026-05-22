import { useReducer, useCallback } from 'react';
import { convertKeys, countPieces } from '../utils';
import { COLOR_WHITE, COLOR_BLACK } from '../constants';

// Типы действий для редьюсера
export const GAME_ACTIONS = {
  SET_WAITING: 'SET_WAITING',
  GAME_STARTED: 'GAME_STARTED',
  MOVE_MADE: 'MOVE_MADE',
  HIGHLIGHTS: 'HIGHLIGHTS',
  GAME_OVER: 'GAME_OVER',
  DESELECT: 'DESELECT',
  SET_MOVE_FROM: 'SET_MOVE_FROM',
  SET_MY_COLOR: 'SET_MY_COLOR',
  SET_LAST_MOVE: 'SET_LAST_MOVE',
  SET_AI_THINKING: 'SET_AI_THINKING',
  CLEAR_CAN_PASS: 'CLEAR_CAN_PASS',
  OPPONENT_DISCONNECTED: 'OPPONENT_DISCONNECTED',
  OPPONENT_RECONNECTED: 'OPPONENT_RECONNECTED',
  DISCONNECT_TICK: 'DISCONNECT_TICK',
  TIMER_TICK: 'TIMER_TICK',
  SET_MOVE_HISTORY: 'SET_MOVE_HISTORY',
  VIEW_HISTORY_MOVE: 'VIEW_HISTORY_MOVE',
  EXIT_HISTORY: 'EXIT_HISTORY',
};

function updateBoardState(state, desk, extra = {}) {
  if (!desk) return { ...state, ...extra };
  const newBoard = convertKeys(desk);
  const counts = countPieces(newBoard);
  return {
    ...state,
    board: newBoard,
    whiteCount: counts.white,
    blackCount: counts.black,
    highlightedEssential: [],
    highlightedCaptured: [],
    ...extra,
  };
}

export const initialGameState = {
  waiting: true,
  joiningError: '',
  myColor: null,
  moversColor: null,
  board: {},
  posForMandatoryCapture: null,
  moveFrom: null,
  canPass: false,
  gameOver: false,
  opponentDisconnected: false,
  disconnectTimeout: 0,
  disconnectCountdown: 0,
  gameOverReason: '',
  winner: '',
  highlightedEssential: [],
  highlightedCaptured: [],
  lastMove: null,
  aiThinking: false,
  whiteCount: 0,
  blackCount: 0,
  timeControl: null,
  timer: null,
  // История ходов
  movesHistory: [],
  viewingHistoryIndex: null,  // индекс просматриваемого хода, null = живая игра
  historyFrom: null,          // подсветка from в режиме истории
  historyTo: null,            // подсветка to в режиме истории
};

export function gameReducer(state, action) {
  switch (action.type) {
    case GAME_ACTIONS.SET_WAITING:
      return { ...state, waiting: true };

    case GAME_ACTIONS.SET_MOVE_FROM:
      return {
        ...state,
        moveFrom: action.payload,
        highlightedEssential: [],
        highlightedCaptured: [],
      };

    case GAME_ACTIONS.DESELECT:
      return { ...state, moveFrom: null, highlightedEssential: [], highlightedCaptured: [] };

    case GAME_ACTIONS.GAME_STARTED:
      return updateBoardState(state, action.payload.desk, {
        moversColor: action.payload.movers_color || COLOR_WHITE,
        waiting: false,
        moveFrom: null,
        timeControl: action.payload.time_control || null,
        timer: action.payload.time || null,
      });

    case GAME_ACTIONS.MOVE_MADE:
      return updateBoardState(state, action.payload.desk, {
        moversColor: action.payload.movers_color || state.moversColor,
        posForMandatoryCapture: action.payload.position_for_mandatory_capture || null,
        canPass: !!action.payload.opportunity_pass_the_move,
        moveFrom: null,
        aiThinking: action.payload.aiThinking ?? false,
        viewingHistoryIndex: null,  // при новом ходе выходим из режима истории
        historyFrom: null,
        historyTo: null,
      });

    case GAME_ACTIONS.HIGHLIGHTS:
      return {
        ...state,
        highlightedEssential: action.payload.essential || [],
        highlightedCaptured: action.payload.captured || [],
      };

    case GAME_ACTIONS.GAME_OVER:
      return updateBoardState(state, action.payload.desk || {}, {
        gameOver: true,
        winner: action.payload.winner || '',
        gameOverReason: action.payload.reason || '',
        moveFrom: null,
        aiThinking: false,
        canPass: false,
        opponentDisconnected: false,
      });

    case GAME_ACTIONS.SET_MY_COLOR:
      return { ...state, myColor: action.payload };
    case GAME_ACTIONS.SET_AI_THINKING:
      return { ...state, aiThinking: action.payload };

    case GAME_ACTIONS.SET_LAST_MOVE:
      return { ...state, lastMove: action.payload };
    case GAME_ACTIONS.CLEAR_CAN_PASS:
      return { ...state, canPass: false };

    case GAME_ACTIONS.OPPONENT_DISCONNECTED:
      return {
        ...state,
        opponentDisconnected: true,
        disconnectTimeout: action.payload.timeout || 30,
        disconnectCountdown: action.payload.timeout || 30,
      };

    case GAME_ACTIONS.OPPONENT_RECONNECTED:
      return {
        ...state,
        opponentDisconnected: false,
        disconnectTimeout: 0,
        disconnectCountdown: 0,
      };

    case GAME_ACTIONS.DISCONNECT_TICK:
      if (state.disconnectCountdown <= 1) {
        return { ...state, disconnectCountdown: 0 };
      }
      return { ...state, disconnectCountdown: state.disconnectCountdown - 1 };

    case GAME_ACTIONS.TIMER_TICK:
      return {
        ...state,
        timer: action.payload,
      };

    case GAME_ACTIONS.SET_MOVE_HISTORY:
      return {
        ...state,
        movesHistory: action.payload,
      };

    case GAME_ACTIONS.VIEW_HISTORY_MOVE: {
      const idx = action.payload;
      const entry = state.movesHistory[idx];
      if (!entry) return state;
      // Загружаем доску из истории (desk — строковые ключи)
      const boardFromHistory = convertKeys(entry.desk || {});
      const counts = countPieces(boardFromHistory);
      return {
        ...state,
        viewingHistoryIndex: idx,
        board: boardFromHistory,
        whiteCount: counts.white,
        blackCount: counts.black,
        historyFrom: entry.from_pos,
        historyTo: entry.to_pos,
        moveFrom: null,
        highlightedEssential: [],
        highlightedCaptured: [],
      };
    }

    case GAME_ACTIONS.EXIT_HISTORY: {
      // Восстанавливаем доску из последнего хода в истории (самое актуальное состояние)
      const lastEntry = state.movesHistory[state.movesHistory.length - 1];
      if (!lastEntry || !lastEntry.desk) return { ...state, viewingHistoryIndex: null, historyFrom: null, historyTo: null };
      const boardLive = convertKeys(lastEntry.desk);
      const counts = countPieces(boardLive);
      return {
        ...state,
        viewingHistoryIndex: null,
        historyFrom: null,
        historyTo: null,
        board: boardLive,
        whiteCount: counts.white,
        blackCount: counts.black,
      };
    }

    default:
      return state;
  }
}

/**
 * Хук для управления состоянием игры через useReducer.
 */
export default function useGameReducer(modeAi) {
  const [state, dispatch] = useReducer(gameReducer, initialGameState);

  const handleServerMessage = useCallback((data) => {
    if (data.status === 'waiting') {
      dispatch({ type: GAME_ACTIONS.SET_WAITING });
      return null;
    }

    if (data.game_over) {
      dispatch({ type: GAME_ACTIONS.GAME_OVER, payload: data });
      return { text: `Игра окончена! Победил ${data.winner || 'ничья'}`, type: 'victory' };
    }

    if (data.message && data.desk) {
      const aiThinking = modeAi && data.movers_color === COLOR_BLACK && !data.game_over;
      // Сохраняем историю ходов
      if (data.move_history) {
        dispatch({ type: GAME_ACTIONS.SET_MOVE_HISTORY, payload: data.move_history });
      }
      dispatch({ type: GAME_ACTIONS.MOVE_MADE, payload: { ...data, aiThinking } });
      return { text: data.message, type: 'info' };
    }

    if (data.essential_positions !== undefined && !data.message) {
      dispatch({
        type: GAME_ACTIONS.HIGHLIGHTS,
        payload: { essential: data.essential_positions || [], captured: data.captured_pieces || [] },
      });
      return null;
    }

    if (data.desk && !data.message) {
      if (data.move_history) {
        dispatch({ type: GAME_ACTIONS.SET_MOVE_HISTORY, payload: data.move_history });
      }
      dispatch({ type: GAME_ACTIONS.GAME_STARTED, payload: data });
      return { text: 'Игра началась!', type: 'info' };
    }

    if (data.status === 'opponent_disconnected') {
      dispatch({ type: GAME_ACTIONS.OPPONENT_DISCONNECTED, payload: data });
      return { text: 'Соперник отключился. Ожидание переподключения...', type: 'warning' };
    }

    if (data.status === 'opponent_reconnected') {
      dispatch({ type: GAME_ACTIONS.OPPONENT_RECONNECTED });
      return { text: 'Соперник вернулся! Игра продолжается.', type: 'info' };
    }

    if (data.type === 'timer_tick') {
      dispatch({ type: GAME_ACTIONS.TIMER_TICK, payload: data.time });
      return null;
    }

    return null;
  }, [modeAi]);

  const selectPiece = useCallback((positionNum) => {
    dispatch({ type: GAME_ACTIONS.SET_MOVE_FROM, payload: positionNum });
  }, []);

  const deselectPiece = useCallback(() => {
    dispatch({ type: GAME_ACTIONS.DESELECT });
  }, []);

  const setLastMove = useCallback((from, to) => {
    dispatch({ type: 'SET_LAST_MOVE', payload: { from, to } });
  }, []);

  return { state, dispatch, handleServerMessage, selectPiece, deselectPiece, setLastMove };
}