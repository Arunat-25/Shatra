import { getPieceColor, getPieceType } from '../utils';
import { getPieceSprite } from './pieceSprites';

export const BOARD_DRAW_THEMES = {
  default: {
    cellLight: '#f4e4b8',
    cellDark: '#c9a55c',
    boardBg: '#f6e7a8',
    boardBorder: 'rgba(154, 102, 0, 0.35)',
    highlightMove: 'rgba(45, 212, 191, 0.85)',
    highlightCapture: 'rgba(248, 113, 113, 0.75)',
    highlightLast: 'rgba(154, 102, 0, 0.45)',
  },
  lite: {
    cellLight: '#faf6ee',
    cellDark: '#9a3412',
    boardBg: '#ddd2c2',
    boardBorder: 'rgba(94, 64, 38, 0.2)',
    highlightMove: 'rgba(45, 212, 191, 0.85)',
    highlightCapture: 'rgba(248, 113, 113, 0.75)',
    highlightLast: 'rgba(154, 102, 0, 0.45)',
  },
};

function resolveTheme(theme) {
  return BOARD_DRAW_THEMES[theme] || BOARD_DRAW_THEMES.default;
}

function cellFill(colorClass, palette) {
  return colorClass === 'cell-dark' ? palette.cellDark : palette.cellLight;
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

function drawPieceShape(ctx, cx, cy, radius, type, color, vectorOnly = false) {
  const sprite = getPieceSprite(type, color, { vectorOnly });
  if (sprite) {
    const size = radius * 2.1;
    ctx.drawImage(sprite, cx - size / 2, cy - size / 2, size, size);
  }
}

const KING_FIELD_NUMBER_COLOR = 'rgba(120, 53, 10, 0.8)';
const LIGHT_CELL_NUMBER_COLOR = 'rgba(40, 28, 16, 0.72)';
const DARK_CELL_NUMBER_COLOR = 'rgba(255, 255, 255, 0.88)';

function cellNumberFontSize(cellSize, scale = 0.19) {
  const minPx = scale <= 0.12 ? 5 : 6;
  return Math.max(minPx, cellSize * scale);
}

function cellNumberInsets(scale = 0.19) {
  return scale <= 0.12 ? { x: 2, y: 1 } : { x: 3, y: 2 };
}

function cellNumberColors(rect) {
  if (rect.sectionClass === 'field-of-king') {
    return {
      fill: KING_FIELD_NUMBER_COLOR,
      shadow: 'rgba(255, 255, 255, 0.9)',
    };
  }
  if (rect.colorClass === 'cell-dark') {
    return {
      fill: DARK_CELL_NUMBER_COLOR,
      shadow: 'rgba(0, 0, 0, 0.75)',
    };
  }
  return {
    fill: LIGHT_CELL_NUMBER_COLOR,
    shadow: 'rgba(255, 255, 255, 0.95)',
  };
}

/**
 * Cell labels — mirrors `.cell-number` in board.css (top-left, tabular).
 */
export function drawCellNumbers(ctx, layout, { scale = 0.19 } = {}) {
  const { x: insetX, y: insetY } = cellNumberInsets(scale);
  const compact = scale <= 0.12;
  const shadowBlur = compact ? 1 : 2;
  const shadowOffsetY = compact ? 0.5 : 1;

  ctx.save();
  ctx.textBaseline = 'top';
  ctx.textAlign = 'left';

  for (const [id, rect] of Object.entries(layout.cells)) {
    const fontSize = cellNumberFontSize(rect.w, scale);
    ctx.font = `700 ${fontSize}px system-ui, -apple-system, sans-serif`;
    const { fill, shadow } = cellNumberColors(rect);
    const x = rect.x + insetX;
    const y = rect.y + insetY;
    const label = String(id);

    ctx.shadowColor = shadow;
    ctx.shadowBlur = shadowBlur;
    ctx.shadowOffsetX = 0;
    ctx.shadowOffsetY = shadowOffsetY;
    ctx.fillStyle = fill;
    ctx.fillText(label, x, y);
  }

  ctx.restore();
}

/** Lite pad fill on canvas (matches `.board.board--lite` pad behind transparent wrapper). */
function drawLiteBoardFrame(ctx, layout) {
  const palette = resolveTheme('lite');
  const frameW = layout.width;
  const frameH = layout.contentHeight ?? layout.height;
  if (!frameW || !frameH) return;

  ctx.save();
  ctx.fillStyle = palette.boardBg;
  ctx.fillRect(0, 0, frameW, frameH);
  ctx.restore();
}

/**
 * @param {CanvasRenderingContext2D} ctx
 */
export function drawBoardFrame(ctx, layout, theme = 'default', myColor = 'белый') {
  if (theme === 'lite') {
    drawLiteBoardFrame(ctx, layout);
    return;
  }
  const palette = resolveTheme(theme);
  const { width, height } = layout;
  const r = 12;
  ctx.save();
  roundRectPath(ctx, 0, 0, width, height, r);
  ctx.fillStyle = palette.boardBg;
  ctx.fill();
  ctx.strokeStyle = palette.boardBorder;
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
  slideOverlay = null,
  hiddenPieceCells = null,
  showCellNumbers = false,
  cellNumberScale = 0.19,
  theme = 'default',
  vectorOnlySprites = false,
}) {
  const palette = resolveTheme(theme);
  const { cells } = layout;
  const hiddenCells = hiddenPieceCells instanceof Set
    ? hiddenPieceCells
    : new Set(hiddenPieceCells || []);

  for (const [, rect] of Object.entries(cells)) {
    ctx.fillStyle = cellFill(rect.colorClass, palette);
    ctx.fillRect(rect.x, rect.y, rect.w, rect.h);
  }

  const essentialSet = new Set(highlightedEssential);
  const capturedSet = new Set(highlightedCaptured);
  const ringWidth = Math.max(1.5, Math.min(3, layout.width / 7 * 0.04));

  for (const [id, rect] of Object.entries(cells)) {
    const cellId = Number(id);
    if (historyFrom === cellId || historyTo === cellId) {
      drawCellHighlight(ctx, rect, palette.highlightLast, ringWidth);
    }
    if (lastMove && (lastMove.from === cellId || lastMove.to === cellId)) {
      drawCellHighlight(ctx, rect, palette.highlightLast, ringWidth);
    }
    if (essentialSet.has(cellId)) {
      drawCellHighlight(ctx, rect, palette.highlightMove, ringWidth);
    }
    if (capturedSet.has(cellId) && !capturedGhostPieces[cellId]) {
      drawCellHighlight(ctx, rect, palette.highlightCapture, ringWidth);
    }
    if (moveFrom === cellId) {
      drawCellHighlight(ctx, rect, palette.highlightMove, ringWidth);
    }
  }

  if (showCellNumbers) {
    drawCellNumbers(ctx, layout, { scale: cellNumberScale });
  }

  for (const essentialId of essentialSet) {
    const rect = cells[essentialId];
    if (!rect) continue;
    const dotR = Math.max(3, Math.min(rect.w, rect.h) * 0.09);
    const cx = rect.x + rect.w / 2;
    const cy = rect.y + rect.h / 2;
    ctx.beginPath();
    ctx.arc(cx, cy, dotR, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(45, 212, 191, 0.5)';
    ctx.fill();
  }

  for (const [id, rect] of Object.entries(cells)) {
    const cellId = Number(id);
    if (hiddenCells.has(cellId)) continue;
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
    drawPieceShape(
      ctx,
      cx,
      cy,
      r,
      getPieceType(piece),
      getPieceColor(piece),
      vectorOnlySprites,
    );
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
      vectorOnlySprites,
    );
  }

  if (slideOverlay?.piece) {
    const r = (slideOverlay.size ?? 40) * 0.38;
    drawPieceShape(
      ctx,
      slideOverlay.x,
      slideOverlay.y,
      r,
      getPieceType(slideOverlay.piece),
      getPieceColor(slideOverlay.piece),
      vectorOnlySprites,
    );
  }
}
