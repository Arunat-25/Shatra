/**
 * AltayOrnament — декоративный SVG-орнамент в алтайском стиле
 * variant: "border" (рамка), "rosette" (розетка), "diamond" (ромб)
 * color: цвет орнамента
 * opacity: прозрачность
 */
export default function AltayOrnament({ variant = 'rosette', color = '#40E0D0', opacity = 0.15 }) {
  const svgProps = {
    className: 'ornament-svg',
    style: { display: 'block', pointerEvents: 'none' },
  };

  if (variant === 'border') {
    // Узорная рамка по периметру
    return (
      <svg {...svgProps} viewBox="0 0 100 100" width="100%" height="100%" opacity={opacity}>
        <defs>
          <pattern id="borderPattern" x="0" y="0" width="10" height="10" patternUnits="userSpaceOnUse">
            {/* Солнечный крест */}
            <circle cx="5" cy="5" r="2" fill="none" stroke={color} strokeWidth="0.5" />
            <path d="M5 1 L5 9 M1 5 L9 5" stroke={color} strokeWidth="0.3" />
            <path d="M2 2 L8 8 M8 2 L2 8" stroke={color} strokeWidth="0.2" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="100" height="100" fill="url(#borderPattern)" />
        {/* Тройная рамка */}
        <rect x="0.5" y="0.5" width="99" height="99" fill="none" stroke={color} strokeWidth="0.5" opacity="0.6" />
        <rect x="1.5" y="1.5" width="97" height="97" fill="none" stroke={color} strokeWidth="0.3" opacity="0.4" />
      </svg>
    );
  }

  if (variant === 'rosette') {
    // Традиционная алтайская розетка (солнечный знак)
    return (
      <svg {...svgProps} viewBox="0 0 20 20" width="100%" height="100%" opacity={opacity}>
        <circle cx="10" cy="10" r="4" fill="none" stroke={color} strokeWidth="0.3" />
        {/* Лепестки */}
        <path d="M10 6 Q12 4 10 2 Q8 4 10 6Z" fill={color} opacity="0.5" />
        <path d="M14 10 Q16 12 18 10 Q16 8 14 10Z" fill={color} opacity="0.5" />
        <path d="M10 14 Q8 16 10 18 Q12 16 10 14Z" fill={color} opacity="0.5" />
        <path d="M6 10 Q4 8 2 10 Q4 12 6 10Z" fill={color} opacity="0.5" />
        {/* Бисерные точки между лепестками */}
        <circle cx="10" cy="4" r="0.4" fill={color} />
        <circle cx="10" cy="16" r="0.4" fill={color} />
        <circle cx="4" cy="10" r="0.4" fill={color} />
        <circle cx="16" cy="10" r="0.4" fill={color} />
        {/* Ромб в центре */}
        <path d="M10 8 L12 10 L10 12 L8 10Z" fill="none" stroke={color} strokeWidth="0.3" />
      </svg>
    );
  }

  if (variant === 'diamond') {
    // Ромбовидный орнамент
    return (
      <svg {...svgProps} viewBox="0 0 20 20" width="100%" height="100%" opacity={opacity}>
        <path d="M10 2 L18 10 L10 18 L2 10Z" fill="none" stroke={color} strokeWidth="0.3" />
        <path d="M10 6 L14 10 L10 14 L6 10Z" fill="none" stroke={color} strokeWidth="0.2" />
        <circle cx="10" cy="10" r="1.5" fill="none" stroke={color} strokeWidth="0.3" />
      </svg>
    );
  }

  // Курганы (стилизованные холмы)
  if (variant === 'kurgan') {
    return (
      <svg {...svgProps} viewBox="0 0 40 10" width="100%" height="100%" opacity={opacity}>
        <path d="M0 8 Q5 2 10 8 Q15 2 20 8 Q25 2 30 8 Q35 2 40 8" fill="none" stroke={color} strokeWidth="0.3" />
        <circle cx="5" cy="5" r="0.5" fill={color} />
        <circle cx="15" cy="5" r="0.5" fill={color} />
        <circle cx="25" cy="5" r="0.5" fill={color} />
        <circle cx="35" cy="5" r="0.5" fill={color} />
      </svg>
    );
  }

  return null;
}