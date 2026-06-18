const ENDPOINT = 'http://127.0.0.1:7570/ingest/7c8a0073-ab4a-4548-b425-fe00951377e1';
const SESSION = '97ed31';

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

export function probeEmblemFlame(tag, extra = {}) {
  const svg = document.querySelector('.lobby-emblem-svg, .auth-card .lobby-emblem-svg, svg.lobby-emblem-svg');
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

  // #region agent log
  fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': SESSION },
    body: JSON.stringify({
      sessionId: SESSION,
      location: 'emblemFlameProbe.js',
      message: 'emblem flame probe',
      hypothesisId: 'H4-centering',
      data,
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion

  return data;
}
