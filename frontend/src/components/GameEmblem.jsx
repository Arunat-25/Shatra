import { useId } from 'react';

/** Эмблема: тренога с кольцом под казан, костёр на земле. */
export default function GameEmblem({ size = 60, className = '' }) {
  const uid = useId().replace(/:/g, '');
  const fireGrad = `campfire-${uid}`;
  const fireHot = `campfire-hot-${uid}`;
  const metalGrad = `hearth-metal-${uid}`;
  const glowGrad = `hearth-glow-${uid}`;
  const groundGrad = `hearth-ground-${uid}`;

  const legStroke = 2.6;
  const ringCx = 30;
  const ringCy = 17;
  const ringRx = 10.5;
  const ringRy = 3.2;

  // Точки крепления ножек к кольцу (120° на эллипсе)
  const attachLeft = { x: 19.5, y: ringCy };
  const attachRight = { x: 40.5, y: ringCy };
  const attachBack = { x: ringCx, y: ringCy - ringRy };

  return (
    <svg
      viewBox="0 0 60 60"
      className={className}
      width={size}
      height={size}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={fireGrad} x1="30" y1="48" x2="30" y2="16" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#8B2500" />
          <stop offset="25%" stopColor="#C0490C" />
          <stop offset="55%" stopColor="#E07A1A" />
          <stop offset="80%" stopColor="#F5C842" />
          <stop offset="100%" stopColor="#FFF0A8" stopOpacity="0.9" />
        </linearGradient>
        <linearGradient id={fireHot} x1="30" y1="46" x2="30" y2="24" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FF6B1A" stopOpacity="0.85" />
          <stop offset="100%" stopColor="#FFF8D0" stopOpacity="0.95" />
        </linearGradient>
        <linearGradient id={metalGrad} x1="20" y1="14" x2="40" y2="52" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#7A6550" />
          <stop offset="100%" stopColor="#3D2E22" />
        </linearGradient>
        <linearGradient id={groundGrad} x1="30" y1="46" x2="30" y2="54" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#4A3728" stopOpacity="0.15" />
          <stop offset="100%" stopColor="#2A1810" stopOpacity="0.35" />
        </linearGradient>
        <radialGradient id={glowGrad} cx="30" cy="46" r="18" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FF8C1A" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#FF8C1A" stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* Земля */}
      <ellipse cx="30" cy="50.5" rx="24" ry="3.5" fill={`url(#${groundGrad})`} />
      <path
        d="M8 50 Q30 48 52 50"
        stroke="#3D2817"
        strokeWidth="1"
        strokeOpacity="0.35"
        fill="none"
      />

      {/* Задняя ножка — от задней точки кольца */}
      <path
        d={`M ${attachBack.x} ${attachBack.y} C ${ringCx} 28 ${ringCx - 0.5} 38 ${ringCx} 49.5`}
        stroke={`url(#${metalGrad})`}
        strokeWidth={legStroke}
        strokeLinecap="round"
        fill="none"
        opacity="0.85"
      />
      <path
        d={`M ${attachBack.x} ${attachBack.y} C ${ringCx} 28 ${ringCx - 0.5} 38 ${ringCx} 49.5`}
        stroke="#9A6600"
        strokeWidth="0.7"
        strokeLinecap="round"
        fill="none"
        opacity="0.35"
      />

      {/* Свечение костра */}
      <ellipse cx="30" cy="46" rx="15" ry="8" fill={`url(#${glowGrad})`} />

      {/* Дрова на земле */}
      <path d="M17 49.5 L43 49.5" stroke="#2A1810" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M20 50.2 L40 48.2" stroke="#3D2817" strokeWidth="1.6" strokeLinecap="round" opacity="0.9" />
      <path d="M22 49 L38 49.8" stroke="#1A1008" strokeWidth="1.2" strokeLinecap="round" opacity="0.7" />

      {/* Костёр на земле */}
      <g className="game-emblem-flame">
        <path
          d="M20 49 C17 47 15 42 16 36 C17 30 19 25 21 22 C22 26 21 32 20 38 C19 44 20 48 20 49 Z"
          fill={`url(#${fireGrad})`}
          opacity="0.95"
        />
        <path
          d="M26 49.5 C22 45 20 38 21 30 C22 23 25 18 27 15 C28 20 27 27 26 34 C25 41 26 47 26 49.5 Z"
          fill={`url(#${fireGrad})`}
        />
        <path
          d="M34 49.5 C30 45 28 38 29 30 C30 23 33 18 35 15 C36 20 35 27 34 34 C33 41 34 47 34 49.5 Z"
          fill={`url(#${fireGrad})`}
          opacity="0.93"
        />
        <path
          d="M40 49 C43 47 45 42 44 36 C43 30 41 25 39 22 C38 26 39 32 40 38 C41 44 40 48 40 49 Z"
          fill={`url(#${fireGrad})`}
          opacity="0.88"
        />
        <path
          d="M23 48.5 C21 45 21 40 23 35 C25 30 28 27 30 26 C32 27 35 30 37 35 C39 40 39 45 37 48.5 C34 50 26 50 23 48.5 Z"
          fill={`url(#${fireHot})`}
          opacity="0.92"
        />
        <circle cx="25" cy="20" r="0.7" fill="#FFE566" opacity="0.7" />
        <circle cx="35" cy="18" r="0.6" fill="#FFE566" opacity="0.65" />
        <circle cx="30" cy="15" r="0.5" fill="#FFF8DC" opacity="0.8" />
      </g>

      {/* Боковые изогнутые ножки — от боковых точек кольца */}
      <path
        d={`M ${attachLeft.x} ${attachLeft.y} C 14 28 11 38 13 49.5`}
        stroke={`url(#${metalGrad})`}
        strokeWidth={legStroke}
        strokeLinecap="round"
        fill="none"
      />
      <path
        d={`M ${attachRight.x} ${attachRight.y} C 46 28 49 38 47 49.5`}
        stroke={`url(#${metalGrad})`}
        strokeWidth={legStroke}
        strokeLinecap="round"
        fill="none"
      />
      <path
        d={`M ${attachLeft.x} ${attachLeft.y} C 14 28 11 38 13 49.5`}
        stroke="#B8956A"
        strokeWidth="0.8"
        strokeLinecap="round"
        fill="none"
        opacity="0.35"
      />
      <path
        d={`M ${attachRight.x} ${attachRight.y} C 46 28 49 38 47 49.5`}
        stroke="#B8956A"
        strokeWidth="0.8"
        strokeLinecap="round"
        fill="none"
        opacity="0.35"
      />

      {/* Кольцо под казан — соединяет ножки */}
      <ellipse
        cx={ringCx}
        cy={ringCy}
        rx={ringRx}
        ry={ringRy}
        fill="none"
        stroke={`url(#${metalGrad})`}
        strokeWidth="2.2"
      />
      <ellipse
        cx={ringCx}
        cy={ringCy}
        rx={ringRx}
        ry={ringRy}
        fill="none"
        stroke="#9A6600"
        strokeWidth="0.7"
        opacity="0.5"
      />
    </svg>
  );
}
