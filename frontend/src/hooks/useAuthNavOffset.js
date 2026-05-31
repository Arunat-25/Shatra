import { useLayoutEffect, useRef } from 'react';

/** Sets --lobby-nav-clear-top = inset-top + nav height + inset-top (same gap above and below nav). */
export default function useAuthNavOffset(deps = []) {
  const navRef = useRef(null);

  useLayoutEffect(() => {
    const el = navRef.current;
    if (!el) return;

    const root = document.documentElement;

    const update = () => {
      const top = Number.parseFloat(getComputedStyle(el).top) || 16;
      const height = el.getBoundingClientRect().height;
      const gap = top;
      root.style.setProperty('--auth-nav-inset-top', `${top}px`);
      root.style.setProperty('--auth-nav-block-height', `${height}px`);
      root.style.setProperty('--lobby-nav-clear-top', `${top + height + gap}px`);
    };

    update();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(update) : null;
    ro?.observe(el);
    window.addEventListener('resize', update);

    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', update);
      root.style.removeProperty('--auth-nav-inset-top');
      root.style.removeProperty('--auth-nav-block-height');
      root.style.removeProperty('--lobby-nav-clear-top');
    };
  }, deps);

  return navRef;
}
