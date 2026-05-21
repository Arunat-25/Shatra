export default function ShatraPiece({ type, color, isSelected, isTarget }) {
  const whiteBody = '#F5F5DC';
  const whiteStroke = '#D2B48C';
  const blackBody = '#1A1A1A';
  const blackStroke = '#444444';
  const goldColor = '#FFD700';
  const fireRed = '#B22222';
  const turquoise = '#40E0D0';

  const pieceColor = color === 'белый' ? whiteBody : blackBody;
  const strokeColor = color === 'белый' ? whiteStroke : blackStroke;
  const runeColor = color === 'белый' ? fireRed : turquoise;
  const glowColor = isSelected ? turquoise : isTarget ? fireRed : 'none';
  const glowAnimation = isTarget ? 'pulse 1.2s ease-in-out infinite' : 'none';
  const isBiy = type === 'бий';
  const isBatyr = type === 'батыр';

  // River stone path — organic, slightly asymmetric
  const stonePath = isBiy
    ? 'M15 2 C20 0, 30 0, 35 2 C42 5, 45 10, 44 18 C43 26, 40 32, 36 36 C32 40, 28 42, 25 42 C22 42, 18 40, 14 36 C10 32, 7 26, 6 18 C5 10, 8 5, 15 2Z'
    : 'M12 4 C18 1, 32 1, 38 4 C44 7, 46 14, 45 22 C44 30, 40 35, 34 38 C28 41, 22 41, 16 38 C10 35, 6 30, 5 22 C4 14, 6 7, 12 4Z';

  // Scale up Biy slightly (taller)
  const viewBox = isBiy ? '0 0 50 44' : '0 0 50 42';

  return (
    <svg
      viewBox={viewBox}
      className="w-full h-full"
      style={{
        filter: `drop-shadow(0 2px 4px rgba(0,0,0,0.4))`,
        display: 'block',
      }}
    >
      {/* Glow filter definitions */}
      <defs>
        <filter id={`glow-${type}-${color}`}>
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        {/* Antler pattern for Biy */}
        <pattern id="antler" x="0" y="0" width="50" height="44" patternUnits="userSpaceOnUse">
          {goldenAntlerPath()}
        </pattern>

        <linearGradient id={`stone-grad-${color}`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={color === 'белый' ? '#FFFDD0' : '#2A2A2A'} />
          <stop offset="100%" stopColor={color === 'белый' ? '#E8DCC8' : '#0A0A0A'} />
        </linearGradient>
      </defs>

      {/* Biy golden halo circle */}
      {isBiy && (
        <circle
          cx="25"
          cy="22"
          r="21"
          fill="none"
          stroke={goldColor}
          strokeWidth="1.2"
          opacity="0.6"
        />
      )}

      {/* Stone body */}
      <path
        d={stonePath}
        fill={`url(#stone-grad-${color})`}
        stroke={isBiy ? goldColor : strokeColor}
        strokeWidth={isBiy ? 1.5 : 1}
        filter={glowColor !== 'none' ? `url(#glow-${type}-${color})` : 'none'}
        style={glowAnimation !== 'none' ? { animation: glowAnimation } : {}}
      />

      {/* Stone texture lines */}
      <path
        d={stonePath}
        fill="none"
        stroke={color === 'белый' ? 'rgba(0,0,0,0.06)' : 'rgba(255,255,255,0.06)'}
        strokeWidth="0.5"
        transform="scale(0.98) translate(0.5, 0.5)"
      />

      {/* Batyr solar rune */}
      {isBatyr && solarRune(color === 'белый', runeColor)}

      {/* Biy golden antler engraving */}
      {isBiy && goldenAntlerPath(goldColor)}
    </svg>
  );
}

function solarRune(isWhite, color) {
  return (
    <g key="solar-rune" fill="none" stroke={color} strokeWidth="1.2" opacity="0.85">
      {/* Central circle */}
      <circle cx="25" cy="20" r="4" />
      {/* Four spiral arms */}
      <path d="M25 16 Q28 12 25 8 Q22 12 25 16Z" />
      <path d="M29 20 Q33 17 35 20 Q33 23 29 20Z" />
      <path d="M25 24 Q22 28 25 32 Q28 28 25 24Z" />
      <path d="M21 20 Q17 17 15 20 Q17 23 21 20Z" />
      {/* Small dots between arms */}
      <circle cx="25" cy="10" r="1" fill={color} />
      <circle cx="35" cy="20" r="1" fill={color} />
      <circle cx="25" cy="30" r="1" fill={color} />
      <circle cx="15" cy="20" r="1" fill={color} />
    </g>
  );
}

function goldenAntlerPath(color = '#FFD700') {
  return (
    <g key="antler" fill="none" stroke={color} strokeWidth="1.1" opacity="0.8">
      {/* Central trunk - stylized deer with antlers, Pazyryk style */}
      {/* Body */}
      <path d="M25 30 Q23 26 24 22 Q25 18 26 22 Q27 26 25 30Z" />
      {/* Left antler */}
      <path d="M24 18 Q20 14 17 10 Q15 8 14 6" />
      <path d="M19 13 Q16 10 15 8" />
      <path d="M17 10 Q13 10 11 8" />
      <path d="M15 8 Q12 7 10 6" />
      {/* Right antler */}
      <path d="M26 18 Q30 14 33 10 Q35 8 36 6" />
      <path d="M31 13 Q34 10 35 8" />
      <path d="M33 10 Q37 10 39 8" />
      <path d="M35 8 Q38 7 40 6" />
      {/* Head */}
      <path d="M22 20 Q23 19 24 20 Q25 19 26 20 Q27 19 28 20" />
      {/* Eyes */}
      <circle cx="23" cy="20.5" r="0.8" fill={color} />
      <circle cx="27" cy="20.5" r="0.8" fill={color} />
    </g>
  );
}