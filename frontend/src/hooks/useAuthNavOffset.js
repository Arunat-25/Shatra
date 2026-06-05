import { useLayoutEffect, useRef } from 'react';

const DEFAULT_CHROME_OFFSET = 72;

/**
 * Measures fixed top chrome and sets --app-top-chrome-offset on :root.
 * When menuToggleRef is provided (compact game nav), only the toggle button is measured.
 */
export default function useAuthNavOffset(
  deps = [],
  topStartRef = null,
  topEndRef = null,
  menuToggleRef = null,
  compactMode = false,
) {
  const navRef = useRef(null);

  useLayoutEffect(() => {
    const root = document.documentElement;

    const update = () => {
      const nav = navRef.current;
      const menuToggle = menuToggleRef?.current;
      let chromeBottom = 0;

      if (compactMode && menuToggle) {
        chromeBottom = menuToggle.getBoundingClientRect().bottom;
      } else {
        const topEnd = topEndRef?.current;
        const topStart = topStartRef?.current;
        if (topEnd) {
          chromeBottom = Math.max(chromeBottom, topEnd.getBoundingClientRect().bottom);
        }
        if (topStart) {
          chromeBottom = Math.max(chromeBottom, topStart.getBoundingClientRect().bottom);
        }
      }

      const gap = compactMode ? 0 : 8;
      const offset =
        chromeBottom > 0 ? Math.ceil(chromeBottom + gap) : DEFAULT_CHROME_OFFSET;

      root.style.setProperty('--app-top-chrome-offset', `${offset}px`);
      root.style.setProperty('--lobby-nav-clear-top', `${offset}px`);

      if (nav) {
        const top = Number.parseFloat(getComputedStyle(nav).top) || 16;
        root.style.setProperty('--auth-nav-inset-top', `${top}px`);
        root.style.setProperty('--auth-nav-block-height', `${nav.getBoundingClientRect().height}px`);
      }
    };

    update();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(update) : null;
    if (navRef.current) ro?.observe(navRef.current);
    if (compactMode && menuToggleRef?.current) {
      ro?.observe(menuToggleRef.current);
    } else {
      if (topStartRef?.current) ro?.observe(topStartRef.current);
      if (topEndRef?.current) ro?.observe(topEndRef.current);
    }
    window.addEventListener('resize', update);

    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', update);
      root.style.removeProperty('--app-top-chrome-offset');
      root.style.removeProperty('--lobby-nav-clear-top');
      root.style.removeProperty('--auth-nav-inset-top');
      root.style.removeProperty('--auth-nav-block-height');
    };
  }, deps);

  return navRef;
}
