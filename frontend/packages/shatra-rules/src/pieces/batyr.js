import { batyrMovesAndCaptures } from '../dictLoader.js';
import { isOwnColor } from '../domain.js';
import { Piece } from './base.js';

export class Batyr extends Piece {
  canMove(cells, fromCell, toCell) {
    if (cells[fromCell] == null) return false;
    if (cells[toCell] != null) return false;

    if (this.color === 'черный' && fromCell >= 1 && fromCell <= 9 && toCell >= 11 && toCell <= 31) {
      return true;
    }
    if (this.color === 'белый' && fromCell >= 54 && fromCell <= 62 && toCell >= 32 && toCell <= 52) {
      return true;
    }

    if (!this.canEnterFortress(cells, toCell)) return false;
    return this.checkPath(cells, fromCell, toCell, false);
  }

  findEnemyCellForCapture(cells, fromCell, toCell) {
    for (const direction of batyrMovesAndCaptures[fromCell] || []) {
      if (!direction.includes(toCell)) continue;
      for (const cell of direction) {
        if (cell === toCell) return null;
        const piece = cells[cell];
        if (piece && !isOwnColor(piece, this.color)) return cell;
      }
    }
    return null;
  }

  canCaptureImpl(cells, fromCell, toCell, capturedThisTurn) {
    const caps = capturedThisTurn || [];
    if (caps.includes(toCell)) return false;
    if (cells[toCell] != null) return false;

    const enemyCell = this.findEnemyCellForCapture(cells, fromCell, toCell);
    if (!enemyCell) return false;
    if (caps.includes(enemyCell)) return false;

    if (this.isEnteringOwnFortress(toCell) && this.isOwnShatraInFortress(cells)) {
      return false;
    }

    return this.checkPath(cells, fromCell, toCell, true, caps);
  }

  isEnteringOwnFortress(toCell) {
    if (this.color === 'черный' && toCell >= 1 && toCell <= 10) return true;
    if (this.color === 'белый' && toCell >= 53 && toCell <= 62) return true;
    return false;
  }

  isOwnShatraInFortress(cells) {
    if (this.color === 'черный') {
      for (let cell = 1; cell < 10; cell += 1) {
        const piece = cells[cell];
        if (piece && piece.includes('черная шатра')) return true;
      }
    } else {
      for (let cell = 54; cell < 63; cell += 1) {
        const piece = cells[cell];
        if (piece && piece.includes('белая шатра')) return true;
      }
    }
    return false;
  }

  canEnterFortress(cells, toCell) {
    if (this.isEnteringOwnFortress(toCell) && this.isOwnShatraInFortress(cells)) {
      return false;
    }
    return true;
  }

  checkPath(cells, fromCell, toCell, capture, pendingCaptures = null) {
    const pending = pendingCaptures || [];

    for (const direction of batyrMovesAndCaptures[fromCell] || []) {
      let piecesCount = 0;
      let enemyCell = null;

      for (const cell of direction) {
        if (cell === toCell) {
          if (piecesCount === 0) {
            return !capture && cells[toCell] == null;
          }
          if (piecesCount === 1 && enemyCell) {
            if (!capture) return false;
            return cells[toCell] == null;
          }
          return false;
        }

        const cellContent = cells[cell];
        const isPending = pending.includes(cell);

        if (cellContent != null || isPending) {
          piecesCount += 1;
          if (cellContent && !isOwnColor(cellContent, this.color)) {
            enemyCell = cell;
          }
        }
      }
    }
    return false;
  }

  getType() {
    return 'батыр';
  }
}
