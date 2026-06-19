import { parsePieceName } from './domain.js';
import { Shatra } from './pieces/shatra.js';
import { Biy } from './pieces/biy.js';
import { Batyr } from './pieces/batyr.js';

export function normalizeCells(cells) {
  const out = {};
  for (const [k, v] of Object.entries(cells || {})) {
    out[Number(k)] = v ?? null;
  }
  return out;
}

export class Board {
  constructor(cells) {
    this.cells = normalizeCells(cells);
    this._pieceCache = new Map();
  }

  getPieceObject(cell) {
    const c = Number(cell);
    if (this._pieceCache.has(c)) return this._pieceCache.get(c);
    const pieceName = this.cells[c];
    if (!pieceName) {
      this._pieceCache.set(c, null);
      return null;
    }
    let piece;
    try {
      const { color, pieceType } = parsePieceName(pieceName);
      if (pieceType === 'шатра') piece = new Shatra(color);
      else if (pieceType === 'бий') piece = new Biy(color);
      else piece = new Batyr(color);
    } catch {
      this._pieceCache.set(c, null);
      return null;
    }
    this._pieceCache.set(c, piece);
    return piece;
  }

  getAllPieces() {
    const result = [];
    for (const [cell, pieceName] of Object.entries(this.cells)) {
      if (!pieceName) continue;
      const piece = this.getPieceObject(Number(cell));
      if (piece) result.push([Number(cell), piece]);
    }
    return result;
  }

  movePiece(fromCell, toCell) {
    const from = Number(fromCell);
    const to = Number(toCell);
    this.cells[to] = this.cells[from];
    this.cells[from] = null;
    this._pieceCache.clear();
  }

  removePiece(cell) {
    this.cells[Number(cell)] = null;
    this._pieceCache.clear();
  }

  copyCells() {
    return { ...this.cells };
  }
}
