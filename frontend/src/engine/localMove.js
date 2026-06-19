import {
  processMove,
  normalizeCells,
  MOVE_REJECT_MESSAGE_CODES,
} from '@shatra/rules';

/**
 * Apply a move locally before the server confirms (optimistic UI).
 * @returns {{ ok: boolean, result: object }}
 */
export function applyLocalMove(gameState, fromCell, toCell) {
  const cells = normalizeCells(gameState.board);
  const chainCell = gameState.posForMandatoryCapture != null
    ? Number(gameState.posForMandatoryCapture)
    : null;

  const result = processMove({
    cells,
    currentColor: gameState.moversColor,
    fromCell: Number(fromCell),
    toCell: Number(toCell),
    chainCaptureCell: chainCell,
    batyrCapturedThisTurn: gameState.batyrCapturedThisTurn || [],
  });

  if (MOVE_REJECT_MESSAGE_CODES.has(result.messageCode)) {
    return { ok: false, result };
  }
  if (!result.updatedPositions) {
    return { ok: false, result };
  }

  return { ok: true, result };
}
