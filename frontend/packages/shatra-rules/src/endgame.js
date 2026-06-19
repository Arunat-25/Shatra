import { Board } from './board.js';

export const DRAW_REPETITION = 'draw.repetition';
export const DRAW_TWO_BIYS = 'draw.two_biys';

function onlyTwoBiysLeft(board) {
  let biyCount = 0;
  let otherCount = 0;
  for (const pieceName of Object.values(board.cells)) {
    if (!pieceName) continue;
    if (pieceName.includes('бий')) biyCount += 1;
    else otherCount += 1;
  }
  return biyCount === 2 && otherCount === 0;
}

export function isGameOver(board, positionHistory = null, movesWithTwoBiys = 0) {
  let biyCount = 0;
  let lastBiyColor = null;
  for (const pieceName of Object.values(board.cells)) {
    if (pieceName && pieceName.includes('бий')) {
      biyCount += 1;
      lastBiyColor = pieceName.includes('бел') ? 'белый' : 'черный';
    }
  }
  if (biyCount === 1) {
    return { over: true, winnerColor: lastBiyColor, drawReason: null };
  }

  if (biyCount === 2 && movesWithTwoBiys >= 3 && onlyTwoBiysLeft(board)) {
    return { over: true, winnerColor: null, drawReason: DRAW_TWO_BIYS };
  }

  if (positionHistory) {
    const posKey = JSON.stringify(Object.entries(board.cells).sort(([a], [b]) => a - b));
    if ((positionHistory[posKey] || 0) >= 3) {
      return { over: true, winnerColor: null, drawReason: DRAW_REPETITION };
    }
  }

  return { over: false, winnerColor: null, drawReason: null };
}

export function recordPosition(positionHistory, positions) {
  const board = new Board(positions);
  const posKey = JSON.stringify(Object.entries(board.cells).sort(([a], [b]) => a - b));
  positionHistory[posKey] = (positionHistory[posKey] || 0) + 1;
}
