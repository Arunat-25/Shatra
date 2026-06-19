import {
  blackBiyPossibleMoves,
  whiteBiyPossibleMoves,
  shatraAndBiyPossibleCaptures,
} from '../dictLoader.js';
import { isOwnColor } from '../domain.js';
import { Piece } from './base.js';

export class Biy extends Piece {
  constructor(color) {
    super(color);
    this.possibleMoves = color === 'черный'
      ? blackBiyPossibleMoves
      : whiteBiyPossibleMoves;
  }

  canMove(cells, fromCell, toCell) {
    if (cells[fromCell] == null) return false;
    if (cells[toCell] != null) return false;
    if (!(this.possibleMoves[fromCell] || []).includes(toCell)) return false;
    return this.canEnterFortress(cells, fromCell, toCell);
  }

  findEnemyCellForCapture(cells, fromCell, toCell) {
    const captures = shatraAndBiyPossibleCaptures[fromCell] || {};
    return captures[toCell] ?? null;
  }

  canCaptureImpl(cells, fromCell, toCell, capturedThisTurn) {
    const enemyCell = this.findEnemyCellForCapture(cells, fromCell, toCell);
    if (enemyCell == null) return false;
    const enemyPiece = cells[enemyCell];
    if (!enemyPiece) return false;
    if (isOwnColor(enemyPiece, this.color)) return false;
    if (cells[toCell] != null) return false;
    return this.canEnterFortress(cells, fromCell, toCell);
  }

  canEnterFortress(cells, fromCell, toCell) {
    if (this.color === 'черный' && toCell >= 1 && toCell <= 10) {
      for (let cell = 1; cell < 10; cell += 1) {
        const piece = cells[cell];
        if (piece && piece.includes('черная шатра')) return false;
      }
      return true;
    }
    if (this.color === 'белый' && toCell >= 53 && toCell <= 62) {
      for (let cell = 54; cell < 63; cell += 1) {
        const piece = cells[cell];
        if (piece && piece.includes('белая шатра')) return false;
      }
      return true;
    }
    return true;
  }

  getType() {
    return 'бий';
  }
}
