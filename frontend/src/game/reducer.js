import { convertKeys, countPieces } from '../utils';
import { COLOR_WHITE } from '../constants';
import { GAME_ACTIONS } from './actions';

export function lastMoveFromPayload(payload) {
  const from = payload?.from_pos;
  const to = payload?.to_pos;
  if (from == null || to == null) return null;
  const f = Number(from);
  const t = Number(to);
  if (!f || !t || f === t) return null;
  return { from: f, to: t };
}

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
  movesHistory: [],
  viewingHistoryIndex: null,
  historyFrom: null,
  historyTo: null,
};

export function gameReducer(state, action) {
  switch (action.type) {
    case GAME_ACTIONS.SET_WAITING:
      return { ...state, waiting: true, joiningError: '' };
    case GAME_ACTIONS.SET_JOINING_ERROR:
      return { ...state, joiningError: action.payload };

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

    case GAME_ACTIONS.MOVE_MADE: {
      const newLastMove = lastMoveFromPayload(action.payload);
      return updateBoardState(state, action.payload.desk, {
        moversColor: action.payload.movers_color || state.moversColor,
        posForMandatoryCapture: action.payload.position_for_mandatory_capture || null,
        canPass: !!action.payload.opportunity_pass_the_move,
        moveFrom: null,
        aiThinking: action.payload.aiThinking ?? false,
        viewingHistoryIndex: null,
        historyFrom: null,
        historyTo: null,
        lastMove: newLastMove ?? state.lastMove,
      });
    }

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
      return { ...state, timer: action.payload };

    case GAME_ACTIONS.SET_MOVE_HISTORY:
      return { ...state, movesHistory: action.payload };

    case GAME_ACTIONS.VIEW_HISTORY_MOVE: {
      const idx = action.payload;
      const entry = state.movesHistory[idx];
      if (!entry) return state;
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
      const lastEntry = state.movesHistory[state.movesHistory.length - 1];
      if (!lastEntry?.desk) {
        return { ...state, viewingHistoryIndex: null, historyFrom: null, historyTo: null };
      }
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
