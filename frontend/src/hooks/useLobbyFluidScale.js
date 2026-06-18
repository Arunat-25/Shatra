import { useLayoutEffect, useRef, useState } from 'react';

const MIN_SCALE = 0.68;
const MAX_SCALE = 1;
const LOBBY_PANEL_GAP_PX = 10;

/**
 * Scales lobby left-panel content to fit the viewport (mobile).
 * Syncs waiting-hall panel height to match mode-selection panel height.
 */
export default function useLobbyFluidScale(enabled, deps = []) {
  const hostRef = useRef(null);
  const contentRef = useRef(null);
  const [layout, setLayout] = useState({ scale: 1, hostHeight: null, panelHeight: null });

  useLayoutEffect(() => {
    if (!enabled) {
      setLayout({ scale: 1, hostHeight: null, panelHeight: null });
      return undefined;
    }

    let frame = 0;

    const measure = () => {
      const host = hostRef.current;
      const content = contentRef.current;
      if (!host || !content) return;

      const panel = host.closest('.lobby-left');
      const layoutEl = panel?.closest('.lobby-layout');
      if (!panel || !layoutEl) return;

      content.style.zoom = '1';
      host.style.height = 'auto';
      panel.style.height = 'auto';
      layoutEl.style.removeProperty('--lobby-panel-height');
      void content.offsetHeight;

      const natural = content.scrollHeight;
      const panelCs = getComputedStyle(panel);
      const padY = parseFloat(panelCs.paddingTop) + parseFloat(panelCs.paddingBottom);
      const panelTop = panel.getBoundingClientRect().top;
      const viewportH = window.visualViewport?.height ?? window.innerHeight;
      const edgeBottom = parseFloat(
        getComputedStyle(document.documentElement).getPropertyValue('--lobby-edge') || '8',
      );
      // Left panel uses the first screen; waiting hall (same height) extends below.
      const maxInnerH = Math.max(
        120,
        viewportH - panelTop - padY - LOBBY_PANEL_GAP_PX - edgeBottom,
      );

      const scale = Math.max(
        MIN_SCALE,
        Math.min(MAX_SCALE, (maxInnerH / natural) * 0.98),
      );

      content.style.zoom = String(scale);
      const hostHeight = content.scrollHeight;
      host.style.height = `${hostHeight}px`;

      const panelHeight = panel.offsetHeight;
      layoutEl.style.setProperty('--lobby-panel-height', `${panelHeight}px`);

      setLayout({ scale, hostHeight, panelHeight, natural, maxInnerH });
    };

    const schedule = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };

    schedule();
    const ro = new ResizeObserver(schedule);
    if (contentRef.current) ro.observe(contentRef.current);
    const panel = hostRef.current?.closest('.lobby-left');
    if (panel) ro.observe(panel);
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
      panel?.closest('.lobby-layout')?.style.removeProperty('--lobby-panel-height');
    };
  }, [enabled, ...deps]);

  return { hostRef, contentRef, ...layout };
}
