import { Board } from './board.js';
import { shatraAndBiyPossibleCaptures } from './dictLoader.js';
import {
  validateMove,
  getAllMandatoryCaptures,
  findCapturedEnemy,
  batyrCanContinueCapture,
} from './hints.js';
import { isGameOver, recordPosition } from './endgame.js';
import {
  TURN_NOW,
  MOVE_PASSED,
  CAPTURE_CONTINUE,
  CAPTURE_CONTINUE_SAME,
  CAPTURE_MUST,
  CAPTURE_MUST_CONTINUE,
  MOVE_UNKNOWN_PIECE,
  PIECE_PROMOTED,
  VALIDATION_TO_MESSAGE,
} from './messageCodes.js';

const PROMOTION_FOR_WHITE = new Set([1, 2, 3]);
const PROMOTION_FOR_BLACK = new Set([60, 61, 62]);

function cloneCells(cells) {
  const out = {};
  for (const [k, v] of Object.entries(cells || {})) {
    out[Number(k)] = v ?? null;
  }
  return out;
}

function opponent(color) {
  return color === 'белый' ? 'черный' : 'белый';
}

function makeResult(fields = {}) {
  return {
    messageCode: '',
    messageParams: {},
    moversColor: null,
    updatedPositions: null,
    capturedPositions: [],
    gameOver: false,
    winnerColor: null,
    drawReason: null,
    opportunityPassTheMove: false,
    positionForMandatoryCapture: null,
    capturedPieces: [],
    ...fields,
  };
}

function validationError(code) {
  return makeResult({
    messageCode: VALIDATION_TO_MESSAGE[code] || 'move.illegal',
  });
}

function gameOverResult(positions, {
  winnerColor = null,
  drawReason = null,
  capturedPositions = [],
  capturedPieces = [],
} = {}) {
  return makeResult({
    moversColor: null,
    updatedPositions: positions,
    gameOver: true,
    winnerColor,
    drawReason,
    capturedPositions,
    capturedPieces,
  });
}

function checkGameEnd(cells, positionHistory, movesWithTwoBiys, { record = true } = {}) {
  if (record) recordPosition(positionHistory, cells);
  const { over, winnerColor, drawReason } = isGameOver(
    new Board(cells),
    positionHistory,
    movesWithTwoBiys,
  );
  return { over, winnerColor, drawReason };
}

function chainCaptureAfterTurn(board, nextPlayer) {
  const mandatoryCaptures = getAllMandatoryCaptures(board, nextPlayer);
  if (!mandatoryCaptures.length) return null;
  const hasNonBiyAttacker = mandatoryCaptures.some(([fromCell]) => {
    const piece = board.getPieceObject(fromCell);
    return piece && piece.getType() !== 'бий';
  });
  if (!hasNonBiyAttacker) return null;
  return mandatoryCaptures[0][0];
}

function promoteShatra(cells, cell, color) {
  const cellName = cells[cell];
  if (!cellName || !cellName.includes('шатра')) return false;
  if (color === 'белый' && PROMOTION_FOR_WHITE.has(cell)) {
    cells[cell] = 'белый батыр';
    return true;
  }
  if (color === 'черный' && PROMOTION_FOR_BLACK.has(cell)) {
    cells[cell] = 'черный батыр';
    return true;
  }
  return false;
}

function executeMove(cells, fromCell, toCell, currentColor, batyrCapturedThisTurn = []) {
  const caps = [...(batyrCapturedThisTurn || [])];
  const newCells = cloneCells(cells);
  const board = new Board(newCells);
  const capturedPositions = [];
  const newBatyrCaptures = [...caps];

  const piece = board.getPieceObject(fromCell);
  if (piece && piece.canCapture(cells, fromCell, toCell, batyrCapturedThisTurn)) {
    const enemyCell = findCapturedEnemy(cells, piece, fromCell, toCell, batyrCapturedThisTurn);
    board.movePiece(fromCell, toCell);
    if (enemyCell != null) {
      board.removePiece(enemyCell);
      capturedPositions.push(enemyCell);
      if (piece.getType() === 'батыр') {
        newBatyrCaptures.push(enemyCell);
      }
    }
    return [board.copyCells(), capturedPositions, newBatyrCaptures];
  }

  board.movePiece(fromCell, toCell);
  if (piece && piece.getType() === 'батыр') {
    newBatyrCaptures.length = 0;
  }
  return [board.copyCells(), capturedPositions, newBatyrCaptures];
}

function finishMove(positions, moverColor, {
  messageCode = '',
  messageParams = {},
  gameOver = false,
  winnerColor = null,
  drawReason = null,
  capturedPositions = [],
  opportunityPass = false,
  mandatoryPos = null,
  capturedPieces = [],
} = {}) {
  return makeResult({
    messageCode,
    messageParams,
    moversColor: opponent(moverColor),
    updatedPositions: positions,
    capturedPositions,
    gameOver,
    winnerColor,
    drawReason,
    opportunityPassTheMove: opportunityPass,
    positionForMandatoryCapture: mandatoryPos,
    capturedPieces,
  });
}

function processChainShatraBiy(
  boardCopy,
  cells,
  currentColor,
  fromCell,
  toCell,
  currentBatyrCaptures,
  piece,
  positionHistory,
  movesWithTwoBiys,
) {
  if (!piece.canCapture(boardCopy, fromCell, toCell, currentBatyrCaptures)) {
    return makeResult({
      messageCode: CAPTURE_MUST,
      moversColor: currentColor,
      updatedPositions: cells,
    });
  }

  const [newCells, capturedPositions, newBatyrCaptures] = executeMove(
    boardCopy,
    fromCell,
    toCell,
    currentColor,
    currentBatyrCaptures,
  );
  promoteShatra(newCells, toCell, currentColor);
  const board = new Board(newCells);
  const pieceKind = piece.getType();

  const { over, winnerColor, drawReason } = checkGameEnd(
    newCells,
    positionHistory,
    movesWithTwoBiys,
  );
  if (over) {
    return gameOverResult(newCells, {
      winnerColor,
      drawReason,
      capturedPositions,
      capturedPieces: newBatyrCaptures,
    });
  }

  let canContinueChain = false;
  const pieceAtLand = board.getPieceObject(toCell);
  if (pieceAtLand) {
    if (pieceAtLand.getType() === 'батыр') {
      canContinueChain = batyrCanContinueCapture(
        board,
        toCell,
        currentColor,
        newBatyrCaptures,
      );
    } else {
      for (const toCellNext of Object.keys(shatraAndBiyPossibleCaptures[toCell] || {})) {
        if (pieceAtLand.canCapture(newCells, toCell, Number(toCellNext), newBatyrCaptures)) {
          canContinueChain = true;
          break;
        }
      }
    }
  }

  const canPassTurn = pieceKind === 'бий' && canContinueChain;
  if (canContinueChain) {
    return makeResult({
      messageCode: CAPTURE_CONTINUE,
      moversColor: currentColor,
      updatedPositions: newCells,
      capturedPositions,
      opportunityPassTheMove: canPassTurn,
      positionForMandatoryCapture: toCell,
      capturedPieces: newBatyrCaptures,
    });
  }

  return finishMove(newCells, currentColor, {
    messageCode: TURN_NOW,
    messageParams: { color: opponent(currentColor) },
    capturedPositions,
    opportunityPass: canPassTurn,
  });
}

function processChainBatyr(
  boardCopy,
  cells,
  currentColor,
  fromCell,
  toCell,
  currentBatyrCaptures,
  piece,
  positionHistory,
  movesWithTwoBiys,
) {
  if (!piece.canCapture(boardCopy, fromCell, toCell, currentBatyrCaptures)) {
    return makeResult({
      messageCode: CAPTURE_MUST_CONTINUE,
      moversColor: currentColor,
      updatedPositions: cells,
    });
  }

  const [newCells, capturedPositions, newBatyrCaptures] = executeMove(
    boardCopy,
    fromCell,
    toCell,
    currentColor,
    currentBatyrCaptures,
  );
  const board = new Board(newCells);

  const { over, winnerColor, drawReason } = checkGameEnd(
    newCells,
    positionHistory,
    movesWithTwoBiys,
  );
  if (over) {
    return gameOverResult(newCells, {
      winnerColor,
      drawReason,
      capturedPositions,
    });
  }

  const canContinue = batyrCanContinueCapture(
    board,
    toCell,
    currentColor,
    newBatyrCaptures,
  );
  if (canContinue) {
    return makeResult({
      messageCode: CAPTURE_CONTINUE,
      moversColor: currentColor,
      updatedPositions: newCells,
      capturedPositions,
      positionForMandatoryCapture: toCell,
      capturedPieces: newBatyrCaptures,
    });
  }

  return finishMove(newCells, currentColor, {
    messageCode: TURN_NOW,
    messageParams: { color: opponent(currentColor) },
    capturedPositions,
    capturedPieces: newBatyrCaptures,
  });
}

function processChainCapture(
  boardCopy,
  cells,
  currentColor,
  fromCell,
  toCell,
  chainCaptureCell,
  currentBatyrCaptures,
  positionHistory,
  movesWithTwoBiys,
) {
  if (fromCell !== chainCaptureCell) {
    return makeResult({
      messageCode: CAPTURE_CONTINUE_SAME,
      moversColor: currentColor,
      updatedPositions: cells,
    });
  }

  const piece = new Board(boardCopy).getPieceObject(fromCell);
  if (piece && (piece.getType() === 'шатра' || piece.getType() === 'бий')) {
    return processChainShatraBiy(
      boardCopy,
      cells,
      currentColor,
      fromCell,
      toCell,
      currentBatyrCaptures,
      piece,
      positionHistory,
      movesWithTwoBiys,
    );
  }
  if (piece && piece.getType() === 'батыр') {
    return processChainBatyr(
      boardCopy,
      cells,
      currentColor,
      fromCell,
      toCell,
      currentBatyrCaptures,
      piece,
      positionHistory,
      movesWithTwoBiys,
    );
  }
  return makeResult({
    messageCode: MOVE_UNKNOWN_PIECE,
    moversColor: currentColor,
    updatedPositions: cells,
  });
}

/**
 * Apply a move locally (mirrors game_engine.moves.process_move).
 */
export function processMove({
  cells,
  currentColor,
  fromCell,
  toCell,
  chainCaptureCell = null,
  batyrCapturedThisTurn = [],
  positionHistory = {},
  movesWithTwoBiys = 0,
}) {
  const currentBatyrCaptures = [...(batyrCapturedThisTurn || [])];
  const boardCopy = cloneCells(cells);
  const history = positionHistory;

  const { over, winnerColor, drawReason } = isGameOver(
    new Board(boardCopy),
    history,
    movesWithTwoBiys,
  );
  if (over) {
    return gameOverResult(cells, { winnerColor, drawReason });
  }

  if (chainCaptureCell === 0) {
    const endCheck = isGameOver(new Board(boardCopy), history, movesWithTwoBiys);
    return finishMove(boardCopy, currentColor, {
      messageCode: MOVE_PASSED,
      gameOver: endCheck.over,
      winnerColor: endCheck.winnerColor,
      drawReason: endCheck.drawReason,
    });
  }

  if (chainCaptureCell != null && chainCaptureCell !== 0) {
    return processChainCapture(
      boardCopy,
      cells,
      currentColor,
      fromCell,
      toCell,
      chainCaptureCell,
      currentBatyrCaptures,
      history,
      movesWithTwoBiys,
    );
  }

  const { valid, code } = validateMove(
    boardCopy,
    fromCell,
    toCell,
    currentColor,
    currentBatyrCaptures,
  );
  if (!valid) {
    return validationError(code);
  }

  const [newCells, capturedPositions, newBatyrCaptures] = executeMove(
    boardCopy,
    fromCell,
    toCell,
    currentColor,
    currentBatyrCaptures,
  );

  let piece = new Board(boardCopy).getPieceObject(fromCell);
  if (!piece) piece = new Board(boardCopy).getPieceObject(toCell);
  let pieceKind = piece ? piece.getType() : '';

  if (pieceKind === 'шатра') {
    if (promoteShatra(newCells, toCell, currentColor)) {
      if (!capturedPositions.length) {
        return finishMove(newCells, currentColor, {
          messageCode: PIECE_PROMOTED,
          messageParams: { color: currentColor },
          capturedPositions,
        });
      }
      pieceKind = 'батыр';
    }
  }

  let end = checkGameEnd(newCells, history, movesWithTwoBiys);
  if (end.over) {
    return gameOverResult(newCells, {
      winnerColor: end.winnerColor,
      drawReason: end.drawReason,
      capturedPositions,
    });
  }

  const hasCaptured = capturedPositions.length > 0;
  let canContinueChain = false;
  if (hasCaptured) {
    if (pieceKind === 'шатра' || pieceKind === 'бий') {
      const pieceAtLand = new Board(newCells).getPieceObject(toCell);
      if (pieceAtLand) {
        for (const toCellNext of Object.keys(shatraAndBiyPossibleCaptures[toCell] || {})) {
          if (pieceAtLand.canCapture(newCells, toCell, Number(toCellNext), newBatyrCaptures)) {
            canContinueChain = true;
            break;
          }
        }
      }
    } else {
      canContinueChain = batyrCanContinueCapture(
        new Board(newCells),
        toCell,
        currentColor,
        newBatyrCaptures,
      );
    }
  }

  const canPassTurn = pieceKind === 'бий' && canContinueChain;
  if (canContinueChain) {
    return makeResult({
      messageCode: CAPTURE_CONTINUE,
      moversColor: currentColor,
      updatedPositions: newCells,
      capturedPositions,
      opportunityPassTheMove: canPassTurn,
      positionForMandatoryCapture: toCell,
      capturedPieces: newBatyrCaptures,
    });
  }

  if (hasCaptured && !canContinueChain) {
    const nextPlayer = opponent(currentColor);
    end = checkGameEnd(newCells, history, movesWithTwoBiys, { record: false });
    return finishMove(newCells, currentColor, {
      messageCode: TURN_NOW,
      messageParams: { color: nextPlayer },
      gameOver: end.over,
      winnerColor: end.winnerColor,
      drawReason: end.drawReason,
      capturedPositions,
      capturedPieces: newBatyrCaptures,
      opportunityPass: canPassTurn,
    });
  }

  const nextPlayer = opponent(currentColor);
  end = checkGameEnd(newCells, history, movesWithTwoBiys, { record: false });
  let chainCapturePos = null;
  if (nextPlayer && !end.over) {
    chainCapturePos = chainCaptureAfterTurn(new Board(newCells), nextPlayer);
  }

  return finishMove(newCells, currentColor, {
    messageCode: TURN_NOW,
    messageParams: { color: nextPlayer },
    gameOver: end.over,
    winnerColor: end.winnerColor,
    drawReason: end.drawReason,
    capturedPositions,
    opportunityPass: canPassTurn,
    mandatoryPos: chainCapturePos,
  });
}
