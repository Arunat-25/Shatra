export const SLIDE_DURATION_MS = 200;

export function easeOutCubic(t) {
  return 1 - (1 - t) ** 3;
}

export function slideDurationMs() {
  if (typeof window === 'undefined' || !window.matchMedia) return SLIDE_DURATION_MS;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : SLIDE_DURATION_MS;
}

/**
 * Animate a point from → to. Returns cancel function.
 * @param {{ from: {x:number,y:number}, to: {x:number,y:number}, duration?: number, onFrame: (t:number,x:number,y:number)=>void, onComplete?: ()=>void }} opts
 */
export function runSlideAnimation({
  from,
  to,
  duration = slideDurationMs(),
  onFrame,
  onComplete,
}) {
  if (duration <= 0) {
    onFrame(1, to.x, to.y);
    onComplete?.();
    return () => {};
  }

  const start = performance.now();
  let raf = null;

  const tick = (now) => {
    const raw = Math.min(1, (now - start) / duration);
    const t = easeOutCubic(raw);
    const x = from.x + (to.x - from.x) * t;
    const y = from.y + (to.y - from.y) * t;
    onFrame(t, x, y);
    if (raw < 1) {
      raf = requestAnimationFrame(tick);
    } else {
      onComplete?.();
    }
  };

  raf = requestAnimationFrame(tick);
  return () => {
    if (raf != null) cancelAnimationFrame(raf);
  };
}
