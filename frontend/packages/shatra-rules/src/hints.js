import { Board } from './board.js';
import {
  shatraAndBiyPossibleCaptures,
  batyrMovesAndCaptures,
  blackShatraPossibleMoves,
  whiteShatraPossibleMoves,
  blackBiyPossibleMoves,
  whiteBiyPossibleMoves,
} from './dictLoader.js';

export function getAllMandatoryCaptures(board, color, batyrCapturedThisTurn = null) {
  const caps = batyrCapturedThisTurn || [];
  const mandatory = [];
  const cells = board.cells;

  for (const [pos, piece] of board.getAllPieces()) {
    if (piece.getColor() !== color) continue;

    const pieceType = piece.getType();
    const candidates = new Set();

    if (pieceType === 'шатра' || pieceType === 'бий') {
      for (const toCell of Object.keys(shatraAndBiyPossibleCaptures[pos] || {})) {
        candidates.add(Number(toCell));
      }
    } else if (pieceType === 'батыр') {
      for (const direction of batyrMovesAndCaptures[pos] || []) {
        for (const target of direction) candidates.add(target);
      }
    }

    for (const toCell of [...candidates].sort((a, b) => a - b)) {
      if (piece.canCapture(cells, pos, toCell, caps)) {
        mandatory.push([pos, toCell]);
      }
    }
  }

  return mandatory;
}

export function validateMove(
  cells,
  fromCell,
  toCell,
  currentColor,
  batyrCapturedThisTurn = null,
  checkMandatory = true,
  chainCaptureCell = null,
) {
  const caps = batyrCapturedThisTurn || [];
  const board = new Board(cells);

  const piece = board.getPieceObject(fromCell);
  if (!piece) return { valid: false, code: 'NO_PIECE' };
  if (piece.getColor() !== currentColor) return { valid: false, code: 'WRONG_COLOR' };
  if (cells[toCell] != null) return { valid: false, code: 'TARGET_OCCUPIED' };

  if (checkMandatory) {
    const mandatoryCaptures = getAllMandatoryCaptures(board, currentColor, caps);
    if (mandatoryCaptures.length > 0) {
      const hasNonBiyAttacker = mandatoryCaptures.some(([f]) => {
        const p = board.getPieceObject(f);
        return p && p.getType() !== 'бий';
      });
      const attackerPositions = new Set(mandatoryCaptures.map(([f]) => f));

      if (!attackerPositions.has(fromCell)) {
        if (hasNonBiyAttacker) {
          return { valid: false, code: 'MANDATORY_CAPTURE_OTHER_PIECE' };
        }
        if (piece.getType() !== 'бий') {
          return { valid: false, code: 'ONLY_BIY_CAN_CAPTURE' };
        }
      } else {
        const captureTargets = new Set(
          mandatoryCaptures.filter(([f]) => f === fromCell).map(([, t]) => t),
        );
        if (!captureTargets.has(toCell)) {
          if (!(piece.getType() === 'бий' && !hasNonBiyAttacker)) {
            return { valid: false, code: 'MANDATORY_CAPTURE_THIS_PIECE' };
          }
        }
      }
    }
  }

  const piece2 = board.getPieceObject(fromCell);
  if (!piece2) return { valid: false, code: 'INTERNAL_NO_PIECE' };

  if (piece2.getType() === 'батыр') {
    for (const direction of batyrMovesAndCaptures[fromCell] || []) {
      if (!direction.includes(toCell)) continue;
      for (const cell of direction) {
        if (cell === toCell) break;
        const cellPiece = cells[cell];
        if (cellPiece && cellPiece.includes(currentColor)) {
          return { valid: false, code: 'OWN_PIECE_BLOCKS_BATYR' };
        }
      }
    }
  }

  if (piece2.canCapture(cells, fromCell, toCell, caps)) {
    return { valid: true, code: 'OK_CAPTURE' };
  }
  if (piece2.canMove(cells, fromCell, toCell)) {
    return { valid: true, code: 'OK_MOVE' };
  }

  return { valid: false, code: 'ILLEGAL_MOVE' };
}

export function findCapturedEnemy(
  cells,
  piece,
  fromCell,
  toCell,
  batyrCapturedThisTurn = null,
) {
  const caps = batyrCapturedThisTurn || [];

  if (piece.getType() === 'шатра' || piece.getType() === 'бий') {
    const captures = shatraAndBiyPossibleCaptures[fromCell] || {};
    return captures[toCell] ?? null;
  }

  if (piece.getType() === 'батыр') {
    const opponentPrefix = piece.getColor() === 'белый' ? 'чер' : 'бел';
    for (const direction of batyrMovesAndCaptures[fromCell] || []) {
      if (!direction.includes(toCell)) continue;
      for (const pos of direction) {
        if (pos === toCell) return null;
        const cellContent = cells[pos];
        if (cellContent && cellContent.includes(opponentPrefix)) {
          if (!caps.includes(pos)) return pos;
          continue;
        }
        if (cellContent != null) return null;
      }
    }
  }

  return null;
}

export function batyrCanContinueCapture(
  board,
  fromCell,
  color,
  batyrCapturedThisTurn = null,
) {
  const caps = batyrCapturedThisTurn || [];
  const piece = board.getPieceObject(fromCell);
  if (!piece || piece.getType() !== 'батыр') return false;

  const cells = board.cells;
  for (const [start, target] of getAllMandatoryCaptures(board, color, caps)) {
    if (start === fromCell && piece.canCapture(cells, fromCell, target, caps)) {
      return true;
    }
  }
  return false;
}

function getAllCandidates(cells, currentColor, fromCell, pieceType) {
  const candidates = new Set();

  if (pieceType === 'шатра' || pieceType === 'бий') {
    const moves = pieceType === 'шатра'
      ? (currentColor === 'черный' ? blackShatraPossibleMoves : whiteShatraPossibleMoves)
      : (currentColor === 'черный' ? blackBiyPossibleMoves : whiteBiyPossibleMoves);
    for (const target of moves[fromCell] || []) candidates.add(target);
    for (const target of Object.keys(shatraAndBiyPossibleCaptures[fromCell] || {})) {
      candidates.add(Number(target));
    }
  } else if (pieceType === 'батыр') {
    for (const direction of batyrMovesAndCaptures[fromCell] || []) {
      for (const target of direction) candidates.add(target);
    }
  }

  return [...candidates];
}

function collectCaptureHighlightCells(cells, fromCell, essentialPositions, piece, batyrCapturedThisTurn) {
  if (!piece || !essentialPositions.length) return [];
  const enemies = new Set();
  for (const toCell of essentialPositions) {
    const enemy = findCapturedEnemy(cells, piece, fromCell, toCell, batyrCapturedThisTurn);
    if (enemy != null) enemies.add(enemy);
  }
  return [...enemies].sort((a, b) => a - b);
}

function getChainHints(cells, currentColor, fromCell, batyrCapturedThisTurn, piece) {
  const allowed = [];
  if (piece.getType() === 'шатра' || piece.getType() === 'бий') {
    for (const toCell of Object.keys(shatraAndBiyPossibleCaptures[fromCell] || {})) {
      const t = Number(toCell);
      if (piece.canCapture(cells, fromCell, t, batyrCapturedThisTurn)) {
        allowed.push(t);
      }
    }
  } else if (piece.getType() === 'батыр') {
    for (const direction of batyrMovesAndCaptures[fromCell] || []) {
      for (const toCell of direction) {
        if (piece.canCapture(cells, fromCell, toCell, batyrCapturedThisTurn)) {
          allowed.push(toCell);
        }
      }
    }
  }
  return allowed;
}

/**
 * @param {object} params
 * @param {Record<number, string|null>} params.cells
 * @param {string} params.currentColor
 * @param {number} params.fromCell
 * @param {number[]} [params.batyrCapturedThisTurn]
 * @param {number|null} [params.chainCaptureCell]
 */
export function getHints({
  cells,
  currentColor,
  fromCell,
  batyrCapturedThisTurn = [],
  chainCaptureCell = null,
}) {
  const caps = [...(batyrCapturedThisTurn || [])];
  const board = new Board(cells);
  const piece = board.getPieceObject(fromCell);

  if (!piece || piece.getColor() !== currentColor) {
    return { essentialPositions: [], capturedPieces: caps, captureHighlightCells: [], messageCode: '' };
  }

  if (chainCaptureCell && chainCaptureCell !== 0) {
    if (fromCell !== chainCaptureCell) {
      return {
        essentialPositions: [],
        capturedPieces: caps,
        captureHighlightCells: [],
        messageCode: 'capture.continue_same',
      };
    }
    const chainAllowed = getChainHints(cells, currentColor, fromCell, caps, piece);
    return {
      essentialPositions: chainAllowed,
      capturedPieces: caps,
      captureHighlightCells: collectCaptureHighlightCells(
        cells, fromCell, chainAllowed, piece, caps,
      ),
      messageCode: '',
    };
  }

  const candidates = getAllCandidates(cells, currentColor, fromCell, piece.getType());
  const allowed = [];
  for (const target of candidates) {
    const { valid } = validateMove(cells, fromCell, target, currentColor, caps, true);
    if (valid) allowed.push(target);
  }

  return {
    essentialPositions: allowed,
    capturedPieces: caps,
    captureHighlightCells: collectCaptureHighlightCells(
      cells, fromCell, allowed, piece, caps,
    ),
    messageCode: '',
  };
}
