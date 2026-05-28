export default function GameEmblem({ size = 60, className = '' }) {
  return (
    <svg viewBox="0 0 60 60" className={className} width={size} height={size} aria-hidden="true">
      <circle cx="30" cy="30" r="28" fill="none" stroke="#9A6600" strokeWidth="1.5" opacity="0.40" />
      <path
        d="M30 8 L34 18 L44 18 L36 24 L38 34 L30 28 L22 34 L24 24 L16 18 L26 18Z"
        fill="none"
        stroke="#106E68"
        strokeWidth="1.2"
        opacity="0.80"
      />
      <circle cx="30" cy="28" r="3" fill="none" stroke="#9A6600" strokeWidth="1" opacity="0.55" />
    </svg>
  );
}
