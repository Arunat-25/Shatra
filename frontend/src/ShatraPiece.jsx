import { useId } from 'react';
import { PIECE_BIY, PIECE_BATYR, COLOR_WHITE } from './constants';

const WHITE_STROKE = '#D2B48C';
const BLACK_STROKE = '#444444';
const GOLD_COLOR = '#FFD700';
const FIRE_RED = '#B22222';
const TURQUOISE = '#40E0D0';

function ShatraPieceLite({ type, color, isSelected, isTarget }) {
  const isWhite = color === COLOR_WHITE;
  const fill = isWhite ? '#fffdd0' : '#2a2a2a';
  const stroke = type === PIECE_BIY ? GOLD_COLOR : (isWhite ? WHITE_STROKE : BLACK_STROKE);
  const isBiy = type === PIECE_BIY;
  const isBatyr = type === PIECE_BATYR;

  const stonePath = isBiy
    ? 'M15 2 C20 0, 30 0, 35 2 C42 5, 45 10, 44 18 C43 26, 40 32, 36 36 C32 40, 28 42, 25 42 C22 42, 18 40, 14 36 C10 32, 7 26, 6 18 C5 10, 8 5, 15 2Z'
    : 'M12 4 C18 1, 32 1, 38 4 C44 7, 46 14, 45 22 C44 30, 40 35, 34 38 C28 41, 22 41, 16 38 C10 35, 6 30, 5 22 C4 14, 6 7, 12 4Z';

  const viewBox = isBiy ? '0 0 50 44' : '0 0 50 42';
  const highlightClass = [
    'shatra-piece-lite',
    isSelected ? 'shatra-piece-lite--selected' : '',
    isTarget ? 'shatra-piece-lite--target' : '',
  ].filter(Boolean).join(' ');

  return (
    <svg viewBox={viewBox} className={highlightClass} style={{ display: 'block' }}>
      {isBiy && (
        <circle cx="25" cy="22" r="21" fill="none" stroke={GOLD_COLOR} strokeWidth="1.2" opacity={0.7} />
      )}
      <path d={stonePath} fill={fill} stroke={stroke} strokeWidth={isBiy ? 1.5 : 1} />
      {isBatyr && solarRune(isWhite, isWhite ? FIRE_RED : TURQUOISE, isSelected)}
      {isBiy && goldenAntlerPath(GOLD_COLOR, isSelected)}
    </svg>
  );
}

export default function ShatraPiece({
  type,
  color,
  isSelected,
  isTarget,
  positionNum,
  variant = 'full',
}) {
  if (variant === 'lite') {
    return (
      <ShatraPieceLite
        type={type}
        color={color}
        isSelected={isSelected}
        isTarget={isTarget}
      />
    );
  }

  const uid = useId();
  const idBase = `${uid}-${positionNum ?? type}`;
  const strokeColor = color === COLOR_WHITE ? WHITE_STROKE : BLACK_STROKE;
  const runeColor = color === COLOR_WHITE ? FIRE_RED : TURQUOISE;
  const glowColor = isSelected ? TURQUOISE : isTarget ? FIRE_RED : 'none';
  const isBiy = type === PIECE_BIY;
  const isBatyr = type === PIECE_BATYR;

  const stonePath = isBiy
    ? 'M15 2 C20 0, 30 0, 35 2 C42 5, 45 10, 44 18 C43 26, 40 32, 36 36 C32 40, 28 42, 25 42 C22 42, 18 40, 14 36 C10 32, 7 26, 6 18 C5 10, 8 5, 15 2Z'
    : 'M12 4 C18 1, 32 1, 38 4 C44 7, 46 14, 45 22 C44 30, 40 35, 34 38 C28 41, 22 41, 16 38 C10 35, 6 30, 5 22 C4 14, 6 7, 12 4Z';

  const viewBox = isBiy ? '0 0 50 44' : '0 0 50 42';

  return (
    <svg
      viewBox={viewBox}
      style={{
        filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.4))',
        display: 'block',
      }}
    >
      <defs>
        <filter id={`glow-select-${idBase}`}>
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <filter id={`glow-target-${idBase}`}>
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <linearGradient id={`stone-grad-${color}-${idBase}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={color === COLOR_WHITE ? '#FFFDD0' : '#2A2A2A'} />
          <stop offset="100%" stopColor={color === COLOR_WHITE ? '#E8DCC8' : '#0A0A0A'} />
        </linearGradient>
      </defs>

      {isBiy && (
        <circle
          cx="25"
          cy="22"
          r="21"
          fill="none"
          stroke={GOLD_COLOR}
          strokeWidth="1.2"
          opacity={isSelected ? 1 : 0.6}
        />
      )}

      <path
        d={stonePath}
        fill={`url(#stone-grad-${color}-${idBase})`}
        stroke={isBiy ? GOLD_COLOR : strokeColor}
        strokeWidth={isBiy ? 1.5 : 1}
        filter={glowColor !== 'none' ? `url(#glow-${isTarget ? 'target' : 'select'}-${idBase})` : 'none'}
        style={{
          transition: 'filter 0.2s ease, stroke 0.2s ease',
          ...(isTarget ? { animation: 'pieceCapture 0.6s ease-out forwards' } : {}),
        }}
      />

      <path
        d={stonePath}
        fill="none"
        stroke={color === COLOR_WHITE ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)'}
        strokeWidth="0.5"
        transform="scale(0.98) translate(0.5, 0.5)"
      />

      {isBatyr && solarRune(color === COLOR_WHITE, runeColor, isSelected)}
      {isBiy && goldenAntlerPath(GOLD_COLOR, isSelected)}
    </svg>
  );
}

function solarRune(isWhite, color, isSelected = false) {
  return (
    <g key="solar-rune" fill="none" stroke={color} strokeWidth={isSelected ? 1.5 : 1.2} opacity={isSelected ? 1 : 0.85}>
      <circle cx="25" cy="20" r="4" />
      <path d="M25 16 Q28 12 25 8 Q22 12 25 16Z" />
      <path d="M29 20 Q33 17 35 20 Q33 23 29 20Z" />
      <path d="M25 24 Q22 28 25 32 Q28 28 25 24Z" />
      <path d="M21 20 Q17 17 15 20 Q17 23 21 20Z" />
      <circle cx="25" cy="10" r={isSelected ? 1.5 : 1} fill={color} />
      <circle cx="35" cy="20" r={isSelected ? 1.5 : 1} fill={color} />
      <circle cx="25" cy="30" r={isSelected ? 1.5 : 1} fill={color} />
      <circle cx="15" cy="20" r={isSelected ? 1.5 : 1} fill={color} />
    </g>
  );
}

function goldenAntlerPath(color = '#FFD700', isSelected = false) {
  return (
    <g key="antler" fill="none" stroke={color} strokeWidth={isSelected ? 1.4 : 1.1} opacity={isSelected ? 1 : 0.8}>
      <path d="M25 30 Q23 26 24 22 Q25 18 26 22 Q27 26 25 30Z" />
      <path d="M24 18 Q20 14 17 10 Q15 8 14 6" />
      <path d="M19 13 Q16 10 15 8" />
      <path d="M17 10 Q13 10 11 8" />
      <path d="M15 8 Q12 7 10 6" />
      <path d="M26 18 Q30 14 33 10 Q35 8 36 6" />
      <path d="M31 13 Q34 10 35 8" />
      <path d="M33 10 Q37 10 39 8" />
      <path d="M35 8 Q38 7 40 6" />
      <path d="M22 20 Q23 19 24 20 Q25 19 26 20 Q27 19 28 20" />
      <circle cx="23" cy="20.5" r={isSelected ? 1.2 : 0.8} fill={color} />
      <circle cx="27" cy="20.5" r={isSelected ? 1.2 : 0.8} fill={color} />
    </g>
  );
}
