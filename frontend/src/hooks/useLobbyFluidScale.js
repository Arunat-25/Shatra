import { useLayoutEffect, useRef, useState } from 'react';

const MIN_SCALE = 0.68;
const MAX_SCALE = 1;

/**
 * Scales lobby left-panel content to fit the viewport (mobile).
 * Uses `zoom` so layout height shrinks with the visual scale ("step back" effect).
 */
export default function useLobbyFluidScale(enabled, deps = []) {
  const hostRef = useRef(null);
  const contentRef = useRef(null);
  const [layout, setLayout] = useState({ scale: 1, hostHeight: null });

  useLayoutEffect(() => {
    if (!enabled) {
      setLayout({ scale: 1, hostHeight: null });
      return undefined;
    }

    let frame = 0;

    const measure = () => {
      const host = hostRef.current;
      const content = contentRef.current;
      if (!host || !content) return;

      const panel = host.closest('.lobby-left');
      if (!panel) return;

      content.style.zoom = '1';
      host.style.height = 'auto';
      panel.style.height = 'auto';
      void content.offsetHeight;

      const natural = content.scrollHeight;
      const panelCs = getComputedStyle(panel);
      const padY = parseFloat(panelCs.paddingTop) + parseFloat(panelCs.paddingBottom);
      const panelTop = panel.getBoundingClientRect().top;
      const viewportH = window.visualViewport?.height ?? window.innerHeight;
      const isSetup = panel.classList.contains('lobby-left--setup');
      const reserveBottom = isSetup ? 48 : 120;
      const maxInnerH = Math.max(120, viewportH - panelTop - reserveBottom - padY);

      const scale = Math.max(
        MIN_SCALE,
        Math.min(MAX_SCALE, (maxInnerH / natural) * 0.98),
      );

      content.style.zoom = String(scale);
      const hostHeight = content.scrollHeight;
      const panelHeight = hostHeight + padY;

      host.style.height = `${hostHeight}px`;
      panel.style.height = `${panelHeight}px`;

      setLayout({ scale, hostHeight, natural, maxInnerH });
    };

    const schedule = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };

    schedule();
    const ro = new ResizeObserver(schedule);
    if (contentRef.current) ro.observe(contentRef.current);
    window.addEventListener('resize', schedule);
    window.visualViewport?.addEventListener('resize', schedule);

    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
      window.removeEventListener('resize', schedule);
      window.visualViewport?.removeEventListener('resize', schedule);
      if (contentRef.current) contentRef.current.style.zoom = '';
      const panel = hostRef.current?.closest('.lobby-left');
      if (panel) panel.style.height = '';
    };
  }, [enabled, ...deps]);

  return { hostRef, contentRef, ...layout };
}
