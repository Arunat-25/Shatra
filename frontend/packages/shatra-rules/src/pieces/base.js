import { isOwnColor } from '../domain.js';

export class Piece {
  constructor(color) {
    this.color = color;
  }

  canCapture(cells, fromCell, toCell, capturedThisTurn = null) {
    const caps = capturedThisTurn || [];
    const enemyCell = this.findEnemyCellForCapture(cells, fromCell, toCell);
    if (enemyCell) {
      const enemyPiece = cells[enemyCell];
      if (enemyPiece && isOwnColor(enemyPiece, this.color)) return false;
    }
    return this.canCaptureImpl(cells, fromCell, toCell, caps);
  }

  // eslint-disable-next-line no-unused-vars
  canCaptureImpl(cells, fromCell, toCell, capturedThisTurn) {
    throw new Error('not implemented');
  }

  // eslint-disable-next-line no-unused-vars
  findEnemyCellForCapture(cells, fromCell, toCell) {
    throw new Error('not implemented');
  }

  // eslint-disable-next-line no-unused-vars
  canMove(cells, fromCell, toCell) {
    throw new Error('not implemented');
  }

  getColor() {
    return this.color;
  }

  getType() {
    throw new Error('not implemented');
  }
}
