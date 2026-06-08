import { convertKeys, countPieces, countPiecesByType } from '../utils';
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
  const countsByType = countPiecesByType(newBoard);
  return {
    ...state,
    board: newBoard,
    whiteCount: counts.white,
    blackCount: counts.black,
    countsByType,
    highlightedEssential: [],
    highlightedCaptured: [],
    capturedGhostPieces: {},
    ...extra,
  };
}

function buildCapturedGhostPieces(state, payload) {
  if (!payload?.position_for_mandatory_capture) return {};

  const ghosts = { ...(state.capturedGhostPieces || {}) };
  for (const pos of payload.captured_positions || []) {
    const cell = Number(pos);
    const piece = state.board?.[cell];
    if (piece) ghosts[cell] = piece;
  }
  return ghosts;
}

export const initialGameState = {
  waiting: true,
  roomType: null,
  showInviteLink: false,
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
  winnerColor: '',
  gameOverMessageCode: '',
  highlightedEssential: [],
  highlightedCaptured: [],
  capturedGhostPieces: {},
  lastMove: null,
  aiThinking: false,
  whiteCount: 0,
  blackCount: 0,
  countsByType: { white: { batyr: 0, shatra: 0, biy: 0 }, black: { batyr: 0, shatra: 0, biy: 0 } },
  timeControl: null,
  increment: null,
  timer: null,
  timerSyncedAt: null,
  movesHistory: [],
  viewingHistoryIndex: null,
  historyFrom: null,
  historyTo: null,
  drawOfferFrom: null,
  rematchReady: false,
  rematchOpponentReady: false,
  rematchUnavailable: false,
  playersInfo: [],
  chatMessages: [],
  chatHidden: false,
};

export function gameReducer(state, action) {
  switch (action.type) {
    case GAME_ACTIONS.RESET_GAME:
      return { ...initialGameState };
    case GAME_ACTIONS.SET_WAITING:
      return { ...state, waiting: true, joiningError: '' };
    case GAME_ACTIONS.SET_WAITING_META:
      return {
        ...state,
        roomType: action.payload?.roomType ?? state.roomType,
        showInviteLink: Boolean(action.payload?.showInviteLink),
      };
    case GAME_ACTIONS.SET_JOINING_ERROR:
      return { ...state, joiningError: action.payload };

    case GAME_ACTIONS.SET_PLAYERS_INFO:
      return { ...state, playersInfo: action.payload || [] };

    case GAME_ACTIONS.CHAT_HISTORY:
      if (state.chatHidden) return state;
      return { ...state, chatMessages: action.payload || [] };

    case GAME_ACTIONS.CHAT_MESSAGE: {
      if (state.chatHidden) return state;
      const next = [...state.chatMessages, action.payload];
      return { ...state, chatMessages: next.slice(-50) };
    }

    case GAME_ACTIONS.TOGGLE_CHAT_HIDDEN: {
      const chatHidden = !state.chatHidden;
      return {
        ...state,
        chatHidden,
        chatMessages: chatHidden ? [] : state.chatMessages,
      };
    }

    case GAME_ACTIONS.SET_MOVE_FROM:
      return {
        ...state,
        moveFrom: action.payload,
        highlightedEssential: [],
        highlightedCaptured: [],
      };

    case GAME_ACTIONS.DESELECT:
      return { ...state, moveFrom: null, highlightedEssential: [], highlightedCaptured: [] };

    case GAME_ACTIONS.GAME_STARTED: {
      const yourColor = action.payload.your_color;
      const myColor = yourColor === 'белый' || yourColor === 'черный'
        ? yourColor
        : state.myColor;
      return updateBoardState(state, action.payload.desk, {
        moversColor: action.payload.movers_color || COLOR_WHITE,
        myColor,
        waiting: false,
        gameOver: false,
        winnerColor: '',
        gameOverReason: '',
        gameOverMessageCode: '',
        moveFrom: null,
        timeControl: action.payload.time_control || null,
        increment: action.payload.increment ?? null,
        timer: action.payload.time || null,
        timerSyncedAt: action.payload.time ? Date.now() : null,
        drawOfferFrom: action.payload.draw_offer_from || null,
        rematchReady: false,
        rematchOpponentReady: false,
        rematchUnavailable: false,
        aiThinking: action.payload.aiThinking ?? false,
        playersInfo: action.payload.players_info || state.playersInfo,
      });
    }

    case GAME_ACTIONS.SET_REMATCH_UNAVAILABLE:
      return {
        ...state,
        rematchUnavailable: true,
        rematchReady: false,
        rematchOpponentReady: false,
      };

    case GAME_ACTIONS.SET_REMATCH_STATUS:
      return {
        ...state,
        rematchReady: !!action.payload.self_ready,
        rematchOpponentReady: !!action.payload.opponent_ready,
      };

    case GAME_ACTIONS.CLEAR_REMATCH:
      return {
        ...state,
        rematchReady: false,
        rematchOpponentReady: false,
        rematchUnavailable: true,
      };

    case GAME_ACTIONS.SET_DRAW_OFFER:
      return { ...state, drawOfferFrom: action.payload };

    case GAME_ACTIONS.GAME_CANCELLED:
      return {
        ...state,
        gameOver: true,
        gameOverReason: 'cancelled',
        winnerColor: action.payload?.winner_color || '',
        gameOverMessageCode: action.payload?.message_code || '',
        drawOfferFrom: null,
        rematchReady: false,
        rematchOpponentReady: false,
        rematchUnavailable: false,
        moveFrom: null,
        canPass: false,
        aiThinking: false,
      };

    case GAME_ACTIONS.MOVE_MADE: {
      const newLastMove = lastMoveFromPayload(action.payload);
      const posForMandatoryCapture = action.payload.position_for_mandatory_capture || null;
      const chainCell = posForMandatoryCapture != null ? Number(posForMandatoryCapture) : null;
      const mover = action.payload.movers_color || state.moversColor;
      const chainActiveForMe = chainCell != null && mover === state.myColor;
      const essential = action.payload.essential_positions;
      const captured = action.payload.captured_pieces;
      return updateBoardState(state, action.payload.desk, {
        moversColor: mover,
        posForMandatoryCapture,
        canPass: !!action.payload.opportunity_pass_the_move,
        moveFrom: chainActiveForMe ? chainCell : null,
        highlightedEssential: essential?.length && chainActiveForMe
          ? essential.map(Number)
          : chainActiveForMe && chainCell
            ? state.highlightedEssential
            : [],
        highlightedCaptured: captured?.length && chainActiveForMe
          ? captured.map(Number)
          : chainActiveForMe && chainCell
            ? state.highlightedCaptured
            : [],
        aiThinking: action.payload.aiThinking ?? false,
        viewingHistoryIndex: null,
        historyFrom: null,
        historyTo: null,
        lastMove: newLastMove ?? state.lastMove,
        capturedGhostPieces: buildCapturedGhostPieces(state, action.payload),
        timer: action.payload.time ?? state.timer,
        timerSyncedAt: action.payload.time ? Date.now() : state.timerSyncedAt,
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
        waiting: false,
        gameOver: true,
        winnerColor: action.payload.winner_color || action.payload.winner || '',
        gameOverReason: action.payload.reason || '',
        gameOverMessageCode: action.payload.message_code || '',
        drawOfferFrom: null,
        rematchReady: false,
        rematchOpponentReady: false,
        rematchUnavailable: false,
        moveFrom: null,
        aiThinking: false,
        canPass: false,
        opponentDisconnected: false,
        movesHistory: action.payload.move_history ?? state.movesHistory,
        moversColor: action.payload.movers_color || state.moversColor,
        timeControl: action.payload.time_control ?? state.timeControl,
        increment: action.payload.increment ?? state.increment,
        timer: action.payload.time ?? state.timer,
        timerSyncedAt: action.payload.time ? Date.now() : state.timerSyncedAt,
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

    case GAME_ACTIONS.SET_DISCONNECT_COUNTDOWN:
      return { ...state, disconnectCountdown: action.payload };

    case GAME_ACTIONS.TIMER_TICK:
      return {
        ...state,
        timer: action.payload,
        timerSyncedAt: Date.now(),
      };

    case GAME_ACTIONS.SET_MOVE_HISTORY:
      return { ...state, movesHistory: action.payload };

    case GAME_ACTIONS.VIEW_HISTORY_MOVE: {
      const idx = action.payload;
      const entry = state.movesHistory[idx];
      if (!entry) return state;
      const boardFromHistory = convertKeys(entry.desk || {});
      const counts = countPieces(boardFromHistory);
      const countsByType = countPiecesByType(boardFromHistory);
      const lastIdx = state.movesHistory.length - 1;
      return {
        ...state,
        // Просмотр последнего хода = live режим (вперёд нельзя)
        viewingHistoryIndex: idx >= lastIdx ? null : idx,
        board: boardFromHistory,
        whiteCount: counts.white,
        blackCount: counts.black,
        countsByType,
        historyFrom: entry.from_pos,
        historyTo: entry.to_pos,
        moveFrom: null,
        highlightedEssential: [],
        highlightedCaptured: [],
        capturedGhostPieces: {},
      };
    }

    case GAME_ACTIONS.HISTORY_STEP_BACK: {
      const lastIdx = state.movesHistory.length - 1;
      if (lastIdx < 0) return state;
      const current = state.viewingHistoryIndex === null ? lastIdx : state.viewingHistoryIndex;
      if (current <= 0) return state;
      return gameReducer(state, { type: GAME_ACTIONS.VIEW_HISTORY_MOVE, payload: current - 1 });
    }

    case GAME_ACTIONS.HISTORY_STEP_FORWARD: {
      const lastIdx = state.movesHistory.length - 1;
      if (lastIdx < 0) return state;
      if (state.viewingHistoryIndex === null) return state; // already live
      const next = state.viewingHistoryIndex + 1;
      if (next >= lastIdx) {
        // forward to live
        return gameReducer(state, { type: GAME_ACTIONS.VIEW_HISTORY_MOVE, payload: lastIdx });
      }
      return gameReducer(state, { type: GAME_ACTIONS.VIEW_HISTORY_MOVE, payload: next });
    }

    case GAME_ACTIONS.EXIT_HISTORY: {
      const lastEntry = state.movesHistory[state.movesHistory.length - 1];
      if (!lastEntry?.desk) {
        return { ...state, viewingHistoryIndex: null, historyFrom: null, historyTo: null };
      }
      const boardLive = convertKeys(lastEntry.desk);
      const counts = countPieces(boardLive);
      const countsByType = countPiecesByType(boardLive);
      return {
        ...state,
        viewingHistoryIndex: null,
        historyFrom: null,
        historyTo: null,
        board: boardLive,
        whiteCount: counts.white,
        blackCount: counts.black,
        countsByType,
      };
    }

    default:
      return state;
  }
}
