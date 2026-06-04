import { getEmptyBoard } from '../../game/startingBoard';

/** Порядок выставления белых шатр из крепости (54 → 62). */
export const FORTRESS_DEPLOY_ORDER = [54, 55, 56, 57, 58, 59, 60, 61, 62];

const WHITE_SHATRA_MOVES = {
  62: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  61: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  60: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  59: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  58: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  57: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  56: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  55: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  54: [52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42, 41, 40, 39, 38, 37, 36, 35, 34, 33, 32],
  52: [51, 45, 44],
  51: [52, 50, 45, 44, 43],
  50: [51, 49, 44, 43, 42],
  49: [50, 48, 43, 42, 41],
  48: [49, 47, 42, 41, 40],
  47: [48, 46, 41, 40, 39],
  46: [47, 40, 39],
  45: [44, 38, 37],
  44: [45, 43, 38, 37, 36],
  43: [44, 42, 37, 36, 35],
  42: [43, 41, 36, 35, 34],
  41: [42, 40, 35, 34, 33],
  40: [41, 39, 34, 33, 32],
  39: [40, 33, 32],
  38: [37, 31, 30],
  37: [38, 36, 31, 30, 29],
  36: [37, 35, 30, 29, 28],
  35: [36, 34, 29, 28, 27],
  34: [35, 33, 28, 27, 26],
  33: [34, 32, 27, 26, 25],
  32: [33, 26, 25],
};

function hasBlockingReserve(board, fromCell) {
  for (let c = 54; c < fromCell; c += 1) {
    const piece = board[c];
    if (piece && piece.includes('белая шатра')) return true;
  }
  return false;
}

export function getNextDeployCell(board) {
  for (const cell of FORTRESS_DEPLOY_ORDER) {
    if (board[cell]?.includes('белая шатра')) return cell;
  }
  return null;
}

export function getDeployTargets(board, fromCell) {
  if (!fromCell || hasBlockingReserve(board, fromCell)) return [];
  const moves = WHITE_SHATRA_MOVES[fromCell] ?? [];
  return moves.filter((t) => t >= 32 && t <= 52 && !board[t]);
}

export function isFortressCell(id) {
  return id >= 54 && id <= 62;
}

export function isMainFieldCell(id) {
  return id >= 11 && id <= 52;
}

export function isMainFieldWhiteShatra(board, id) {
  const piece = board[id];
  return isMainFieldCell(id) && piece?.includes('белая шатра');
}

export function getMainFieldShatraTargets(board, fromCell) {
  const moves = WHITE_SHATRA_MOVES[fromCell] ?? [];
  return moves.filter((t) => isMainFieldCell(t) && !board[t]);
}

export function buildFortressLessonBoard(deployments, blackBiyCell) {
  const b = getEmptyBoard();
  for (let c = 54; c <= 62; c += 1) {
    b[c] = 'белая шатра';
  }
  for (const { from, to } of deployments) {
    b[from] = null;
    b[to] = 'белая шатра';
  }
  b[11] = null;
  b[12] = null;
  b[blackBiyCell] = 'черный бий';
  return b;
}

/** Позиция чёрного бия после n выставлений (0 — старт на 11, далее 11↔12). */
export function getBlackBiyCellAfterDeploy(deployCount) {
  return deployCount % 2 === 0 ? 11 : 12;
}

/** Урок: взятие в крепости — 60/61/62 берут 58 на 56/55/54. */
export const FORTRESS_CAPTURE_PIECES = {
  60: { 56: 58 },
  61: { 55: 58 },
  62: { 54: 58 },
};

export function canFortressCaptureFrom(cell) {
  return cell in FORTRESS_CAPTURE_PIECES;
}

export function getFortressCaptureTargets(fromCell) {
  const caps = FORTRESS_CAPTURE_PIECES[fromCell];
  return caps ? Object.keys(caps).map(Number) : [];
}

/** Белая половина большого поля (выставление из крепости). */
export const WHITE_MAIN_FIELD_DEPLOY = [
  32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52,
];

/** Шаг 6: все ходы по game_engine (get_hints + выставление батыра). */
export const RESERVE_BIY_54_TARGETS = [
  32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 55,
  57, 58,
];
export const RESERVE_BATYR_62_TARGETS = [
  32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 56, 58, 59,
  60, 61,
];

/** Урок: бий и батыр не бьют в крепость/ворота при своих шатрах в резерве. */
/** Ходы сверены с game_engine (get_hints) для позиции урока. */
export const FORTRESS_BIY_BATYR_STEP = {
  0: {
    pieces: {
      42: {
        piece: 'белый бий',
        allowedTargets: [34, 35, 36, 41, 43, 48],
      },
      38: {
        piece: 'белый батыр',
        allowedTargets: [14, 17, 22, 24, 30, 31, 32, 33, 34, 35, 36, 37, 44, 45, 52],
      },
      61: {
        piece: 'белая шатра',
        allowedTargets: [
          32, 33, 34, 35, 36, 37, 39, 40, 41, 43, 44, 45, 46, 47, 48, 51, 52,
        ],
      },
      62: {
        piece: 'белая шатра',
        allowedTargets: [],
      },
    },
    blackPieces: { 49: 'черная шатра', 50: 'черная шатра' },
    selectHintKey: 'tutorial.section5.biyBatyrSelectHint',
    targetHintKey: 'tutorial.section5.biyBatyrTargetHint',
    noMovesHintKey: 'tutorial.section5.biyBatyrNoMovesHint',
    textKey: 'tutorial.section5.step3.text',
  },
  1: {
    chains: {
      42: [
        { piecePos: 42, piece: 'белый бий', captures: { 53: 49 } },
        { piecePos: 53, piece: 'белый бий', captures: { 40: 48 } },
      ],
      32: [
        {
          piecePos: 32,
          piece: 'белый батыр',
          captures: { 53: 48, 56: 48 },
          branches: { 53: { complete: true }, 56: { complete: true } },
        },
      ],
    },
    blackPieces: { 48: 'черная шатра', 49: 'черная шатра' },
    selectHintKey: 'tutorial.section5.biyBatyrSelectHint',
    targetHintKey: 'tutorial.section5.biyBatyrTargetHint',
    chainContinueHintKey: 'tutorial.section5.step4ChainHint',
    textKey: 'tutorial.section5.step4.text',
  },
  2: {
    pieces: {
      46: {
        piece: 'белая шатра',
        allowedTargets: [48],
        captures: { 48: 47 },
      },
    },
    blackPieces: { 47: 'черная шатра', 53: 'черная шатра' },
    boardPieces: { 17: 'белый бий' },
    selectHintKey: 'tutorial.section5.shatraFortressSelectHint',
    targetHintKey: 'tutorial.section5.biyBatyrTargetHint',
    textKey: 'tutorial.section5.step5.text',
  },
  3: {
    fillBlackFortress: true,
    pieces: {
      54: {
        piece: 'белый бий',
        allowedTargets: [...RESERVE_BIY_54_TARGETS],
      },
      62: {
        piece: 'белый батыр',
        allowedTargets: [...RESERVE_BATYR_62_TARGETS],
      },
    },
    selectHintKey: 'tutorial.section5.reserveDeploySelectHint',
    targetHintKey: 'tutorial.section5.reserveDeployTargetHint',
    textKey: 'tutorial.section5.step6.text',
  },
};

export function buildFortressCaptureBoard(captureResult) {
  const b = getEmptyBoard();
  b[60] = 'белая шатра';
  b[61] = 'белая шатра';
  b[62] = 'белая шатра';
  b[58] = 'черная шатра';
  if (captureResult) {
    const { from, to } = captureResult;
    b[from] = null;
    b[to] = 'белая шатра';
    b[58] = null;
  }
  return b;
}
