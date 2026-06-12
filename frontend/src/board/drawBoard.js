import { getPieceColor, getPieceType } from '../utils';
import { getPieceSprite, preloadPieceSprites } from './pieceSprites';

preloadPieceSprites();

const CELL_LIGHT = '#f4e4b8';
const CELL_DARK = '#c9a55c';
const HIGHLIGHT_MOVE = 'rgba(45, 212, 191, 0.85)';
const HIGHLIGHT_CAPTURE = 'rgba(248, 113, 113, 0.75)';
const HIGHLIGHT_LAST = 'rgba(154, 102, 0, 0.45)';
const BOARD_BG = '#f6e7a8';
const BOARD_BORDER = 'rgba(154, 102, 0, 0.35)';

function cellFill(colorClass) {
  return colorClass === 'cell-dark' ? CELL_DARK : CELL_LIGHT;
}

function roundRectPath(ctx, x, y, w, h, r) {
  if (typeof ctx.roundRect === 'function') {
    ctx.beginPath();
    ctx.roundRect(x, y, w, h, r);
    return;
  }
  const radius = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.arcTo(x + w, y, x + w, y + h, radius);
  ctx.arcTo(x + w, y + h, x, y + h, radius);
  ctx.arcTo(x, y + h, x, y, radius);
  ctx.arcTo(x, y, x + w, y, radius);
  ctx.closePath();
}

function drawCellHighlight(ctx, rect, color, lineWidth) {
  const inset = Math.max(2, rect.w * 0.06);
  ctx.strokeStyle = color;
  ctx.lineWidth = lineWidth;
  ctx.strokeRect(
    rect.x + inset,
    rect.y + inset,
    rect.w - inset * 2,
    rect.h - inset * 2,
  );
}

function drawPieceShape(ctx, cx, cy, radius, type, color) {
  const sprite = getPieceSprite(type, color);
  if (sprite) {
    const size = radius * 2.1;
    ctx.drawImage(sprite, cx - size / 2, cy - size / 2, size, size);
    return;
  }
}

/**
 * @param {CanvasRenderingContext2D} ctx
 */
export function drawBoardFrame(ctx, layout) {
  const { width, height } = layout;
  const r = 12;
  ctx.save();
  roundRectPath(ctx, 0, 0, width, height, r);
  ctx.fillStyle = BOARD_BG;
  ctx.fill();
  ctx.strokeStyle = BOARD_BORDER;
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.restore();
}

/**
 * @param {CanvasRenderingContext2D} ctx
 */
export function drawBoardState(ctx, layout, {
  board,
  moveFrom,
  highlightedEssential = [],
  highlightedCaptured = [],
  capturedGhostPieces = {},
  lastMove = null,
  historyFrom = null,
  historyTo = null,
  dragGhost = null,
}) {
  const { cells } = layout;

  for (const [id, rect] of Object.entries(cells)) {
    const cellId = Number(id);
    ctx.fillStyle = cellFill(rect.colorClass);
    ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
  }

  const essentialSet = new Set(highlightedEssential);
  const capturedSet = new Set(highlightedCaptured);

  for (const [id, rect] of Object.entries(cells)) {
    const cellId = Number(id);
    if (historyFrom === cellId || historyTo === cellId) {
      drawCellHighlight(ctx, rect, HIGHLIGHT_LAST, 2);
    }
    if (lastMove && (lastMove.from === cellId || lastMove.to === cellId)) {
      drawCellHighlight(ctx, rect, HIGHLIGHT_LAST, 2);
    }
    if (essentialSet.has(cellId)) {
      drawCellHighlight(ctx, rect, HIGHLIGHT_MOVE, 3);
    }
    if (capturedSet.has(cellId) && !capturedGhostPieces[cellId]) {
      drawCellHighlight(ctx, rect, HIGHLIGHT_CAPTURE, 3);
    }
    if (moveFrom === cellId) {
      drawCellHighlight(ctx, rect, HIGHLIGHT_MOVE, 3);
    }
  }

  for (const [id, rect] of Object.entries(cells)) {
    const cellId = Number(id);
    const piece = board[cellId] || capturedGhostPieces[cellId];
    if (!piece) continue;
    const cx = rect.x + rect.w / 2;
    const cy = rect.y + rect.h / 2;
    const r = Math.min(rect.w, rect.h) * 0.38;
    const isDragOrigin = dragGhost && dragGhost.fromId === cellId;
    if (isDragOrigin) {
      ctx.save();
      ctx.globalAlpha = 0.35;
    }
    drawPieceShape(ctx, cx, cy, r, getPieceType(piece), getPieceColor(piece));
    if (isDragOrigin) {
      ctx.restore();
    }
  }

  if (dragGhost?.piece) {
    const r = (dragGhost.size ?? 40) * 0.38;
    drawPieceShape(
      ctx,
      dragGhost.x,
      dragGhost.y,
      r,
      getPieceType(dragGhost.piece),
      getPieceColor(dragGhost.piece),
    );
  }
}
