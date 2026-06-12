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

function drawVectorPiece(ctx, type, color) {
  const isWhite = color === COLOR_WHITE;
  const fill = isWhite ? '#fffdd0' : '#2a2a2a';
  const stroke = isWhite ? '#d2b48c' : '#444';
  const cx = SPRITE_SIZE / 2;
  const cy = SPRITE_SIZE / 2;
  const radius = SPRITE_SIZE * 0.38;

  ctx.clearRect(0, 0, SPRITE_SIZE, SPRITE_SIZE);
  ctx.beginPath();
  ctx.ellipse(cx, cy, radius * 0.92, radius * 0.82, 0, 0, Math.PI * 2);
  ctx.fillStyle = fill;
  ctx.fill();
  ctx.strokeStyle = type === PIECE_BIY ? '#ffd700' : stroke;
  ctx.lineWidth = type === PIECE_BIY ? 1.5 : 1;
  ctx.stroke();

  if (type === PIECE_BIY) {
    ctx.beginPath();
    ctx.arc(cx, cy, radius * 0.78, 0, Math.PI * 2);
    ctx.strokeStyle = '#ffd700';
    ctx.lineWidth = 1;
    ctx.stroke();
  } else if (type === PIECE_BATYR) {
    ctx.fillStyle = isWhite ? '#b22222' : '#40e0d0';
    ctx.beginPath();
    ctx.arc(cx, cy - radius * 0.15, radius * 0.18, 0, Math.PI * 2);
    ctx.fill();
  } else if (type === PIECE_SHATRA) {
    ctx.fillStyle = isWhite ? '#9a6600' : '#40e0d0';
    ctx.font = `bold ${Math.round(radius * 0.5)}px sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('♔', cx, cy);
  }
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
