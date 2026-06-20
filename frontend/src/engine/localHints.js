import { getHints, normalizeCells } from '@shatra/rules';

/**
 * Compute legal destinations locally (no WebSocket round-trip).
 * @param {object} gameState — gameReducer state
 * @param {number} fromCell
 */
export function computeLocalHints(gameState, fromCell) {
  const board = normalizeCells(gameState.board);
  const chainCell = gameState.posForMandatoryCapture != null
    ? Number(gameState.posForMandatoryCapture)
    : null;
  const batyrCaptured = gameState.batyrCapturedThisTurn || [];

  const result = getHints({
    cells: board,
    currentColor: gameState.moversColor,
    fromCell: Number(fromCell),
    batyrCapturedThisTurn: batyrCaptured,
    chainCaptureCell: chainCell,
  });

  return {
    essential: result.essentialPositions || [],
    captured: result.captureHighlightCells || [],
    messageCode: result.messageCode || '',
  };
}
