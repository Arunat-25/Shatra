import { sendDevProbe } from './devProbe';

function rect(el) {
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {
    h: Math.round(r.height),
    w: Math.round(r.width),
    top: Math.round(r.top),
    bottom: Math.round(r.bottom),
  };
}

/** Debug probe: lobby emblem flame alignment. Dev only. */
export function probeEmblemFlame(tag, extra = {}) {
  const emblemSvg = document.querySelector('.lobby-emblem-svg') || document.querySelector('.auth-card svg');
  const flame = emblemSvg?.querySelector('.game-emblem-flame');
  const logs = emblemSvg?.querySelector('path[d="M17 49.5 L43 49.5"]');
  const samplePath = flame?.querySelector('path:nth-child(2)');
  const left = document.querySelector('.lobby-left');
  const emblemEl = emblemSvg?.closest('.lobby-emblem') || emblemSvg;
  const centerX = (el) => (el ? el.getBoundingClientRect().left + el.getBoundingClientRect().width / 2 : null);

  const data = {
    tag,
    path: window.location.pathname,
    viewport: { w: window.innerWidth, h: window.innerHeight },
    emblem: rect(emblemSvg?.closest('.lobby-emblem') || emblemSvg),
    svg: rect(emblemSvg),
    flame: rect(flame),
    logs: rect(logs),
    flameVsLogsBottom: flame && logs
      ? Math.round(flame.getBoundingClientRect().bottom - logs.getBoundingClientRect().bottom)
      : null,
    flameGroupOrigin: flame ? getComputedStyle(flame).transformOrigin : null,
    pathOrigin: samplePath ? getComputedStyle(samplePath).transformOrigin : null,
    pathAnim: samplePath ? getComputedStyle(samplePath).animationName : null,
    fluidZoom: getComputedStyle(document.querySelector('.lobby-left-inner--fluid') || document.body).zoom,
    centering: left && emblemEl ? {
      leftCx: Math.round(centerX(left)),
      emblemCx: Math.round(centerX(emblemEl)),
      offsetPx: Math.round(centerX(emblemEl) - centerX(left)),
    } : null,
    misaligned: left && emblemEl
      ? Math.abs(Math.round(centerX(emblemEl) - centerX(left))) > 2
      : false,
    ...extra,
  };

  sendDevProbe({
    sessionId: 'dev',
    hypothesisId: 'emblem-flame',
    location: 'emblemFlameProbe.js',
    message: 'emblem flame probe',
    data,
  });

  return data;
}
