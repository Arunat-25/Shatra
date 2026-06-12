import { COLOR_BLACK, COLOR_WHITE, PIECE_BATYR, PIECE_BIY, PIECE_SHATRA } from '../constants';

const SPRITE_SIZE = 64;
const SPRITE_PATHS = {
  [`${COLOR_WHITE}:${PIECE_BIY}`]: '/images/pieces/white-biy.webp',
  [`${COLOR_WHITE}:${PIECE_BATYR}`]: '/images/pieces/white-batyr.webp',
  [`${COLOR_WHITE}:${PIECE_SHATRA}`]: '/images/pieces/white-shatra.webp',
  [`${COLOR_BLACK}:${PIECE_BIY}`]: '/images/pieces/black-biy.webp',
  [`${COLOR_BLACK}:${PIECE_BATYR}`]: '/images/pieces/black-batyr.webp',
  [`${COLOR_BLACK}:${PIECE_SHATRA}`]: '/images/pieces/black-shatra.webp',
};

const cache = new Map();
let preloadPromise = null;

function drawStone(ctx, cx, cy, radius, fill, stroke, strokeWidth = 1) {
  ctx.beginPath();
  ctx.ellipse(cx, cy, radius * 0.92, radius * 0.82, 0, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = stroke;
  ctx.lineWidth = strokeWidth;
  ctx.stroke();
}

function drawBiyAntlers(ctx, cx, cy, color) {
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  ctx.moveTo(cx, cy - 8);
  ctx.lineTo(cx - 8, cy - 18);
  ctx.moveTo(cx, cy - 8);
  ctx.lineTo(cx + 8, cy - 18);
  ctx.moveTo(cx - 3, cy - 12);
  ctx.lineTo(cx - 10, cy - 16);
  ctx.moveTo(cx + 3, cy - 12);
  ctx.lineTo(cx + 10, cy - 16);
  ctx.stroke();
}

function drawVectorPiece(ctx, type, color) {
  const isWhite = color === COLOR_WHITE;
  const fill = isWhite ? '#fffdd0' : '#2a2a2a';
  const stroke = isWhite ? '#d2b48c' : '#444';
  const cx = SPRITE_SIZE / 2;
  const cy = SPRITE_SIZE / 2;
  const radius = SPRITE_SIZE * 0.38;

  ctx.clearRect(0, 0, SPRITE_SIZE, SPRITE_SIZE);

  if (type === PIECE_BIY) {
    drawStone(ctx, cx, cy, radius, fill, '#ffd700', 1.5);
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 0.78, 0, Math.PI * 2);
    ctx.strokeStyle = '#ffd700';
    ctx.lineWidth = 1;
    ctx.stroke();
    drawBiyAntlers(ctx, cx, cy, '#ffd700');
    return;
  }

  drawStone(ctx, cx, cy, radius, fill, stroke, 1);

  if (type === PIECE_BATYR) {
    ctx.strokeStyle = isWhite ? '#b22222' : '#40e0d0';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(cx, cy - 3, radius * 0.18, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(cx, cy - 8);
    ctx.lineTo(cx, cy - 14);
    ctx.moveTo(cx - 4, cy - 10);
    ctx.lineTo(cx + 4, cy - 10);
    ctx.moveTo(cx, cy - 14);
    ctx.lineTo(cx - 3, cy - 18);
    ctx.moveTo(cx, cy - 14);
    ctx.lineTo(cx + 3, cy - 18);
    ctx.stroke();
  }
  // шатра — plain stone only (matches DOM ShatraPiece)
}

function createVectorSprite(type, color) {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  canvas.width = SPRITE_SIZE;
  canvas.height = SPRITE_SIZE;
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  drawVectorPiece(ctx, type, color);
  return canvas;
}

function loadImage(src) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

/**
 * Preload piece sprites (webp with vector fallback per piece).
 */
export function preloadPieceSprites() {
  if (preloadPromise) return preloadPromise;

  preloadPromise = Promise.all(
    Object.entries(SPRITE_PATHS).map(async ([key, src]) => {
      const [color, type] = key.split(':');
      const img = await loadImage(src);
      cache.set(key, img || createVectorSprite(type, color));
    }),
  );

  return preloadPromise;
}

export function getPieceSprite(type, color) {
  const key = `${color}:${type}`;
  if (!cache.has(key)) {
    cache.set(key, createVectorSprite(type, color));
    const src = SPRITE_PATHS[key];
    if (src) {
      loadImage(src).then((img) => {
        if (img) cache.set(key, img);
      });
    }
  }
  return cache.get(key);
}

/** @internal test hook */
export function __drawVectorPieceForTest(ctx, type, color) {
  drawVectorPiece(ctx, type, color);
}
