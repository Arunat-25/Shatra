import {
  blackShatraPossibleMoves,
  whiteShatraPossibleMoves,
  shatraAndBiyPossibleCaptures,
} from '../dictLoader.js';
import { isOwnColor } from '../domain.js';
import { Piece } from './base.js';

export class Shatra extends Piece {
  constructor(color) {
    super(color);
    this.possibleMoves = color === 'черный'
      ? blackShatraPossibleMoves
      : whiteShatraPossibleMoves;
  }

  canMove(cells, fromCell, toCell) {
    if (cells[fromCell] == null) return false;
    if (cells[toCell] != null) return false;
    if (!(this.possibleMoves[fromCell] || []).includes(toCell)) return false;

    if (this.color === 'черный' && fromCell >= 1 && fromCell <= 9) {
      for (let cell = fromCell + 1; cell < 10; cell += 1) {
        const piece = cells[cell];
        if (piece && piece.includes('черная шатра')) return false;
      }
    } else if (this.color === 'белый' && fromCell >= 54 && fromCell <= 62) {
      for (let cell = 54; cell < fromCell; cell += 1) {
        const piece = cells[cell];
        if (piece && piece.includes('белая шатра')) return false;
      }
    }
    return true;
  }

  findEnemyCellForCapture(cells, fromCell, toCell) {
    const captures = shatraAndBiyPossibleCaptures[fromCell] || {};
    return captures[toCell] ?? null;
  }

  canCaptureImpl(cells, fromCell, toCell, capturedThisTurn) {
    const caps = capturedThisTurn || [];
    const enemyCell = this.findEnemyCellForCapture(cells, fromCell, toCell);
    if (enemyCell == null) return false;
    const enemyPiece = cells[enemyCell];
    if (!enemyPiece) return false;
    if (isOwnColor(enemyPiece, this.color)) return false;
    if (cells[toCell] != null) return false;
    if (caps.includes(enemyCell)) return false;
    return this.canEnterFortress(cells, fromCell, toCell);
  }

  canEnterFortress(cells, fromCell, toCell) {
    if (this.color === 'черный' && toCell >= 1 && toCell <= 10) return false;
    if (this.color === 'белый' && toCell >= 53 && toCell <= 62) return false;
    return true;
  }

  getType() {
    return 'шатра';
  }
}
