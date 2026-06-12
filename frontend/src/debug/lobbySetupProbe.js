/** Debug probe: lobby mode buttons / setup picker clipping (session 97ed31). */

function rectSummary(el) {
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {
    top: Math.round(r.top),
    bottom: Math.round(r.bottom),
    h: Math.round(r.height),
    clientH: el.clientHeight,
    scrollH: el.scrollHeight,
    overflowY: getComputedStyle(el).overflowY,
  };
}

function buttonVisibility(root, selector) {
  const rootR = root?.getBoundingClientRect();
  if (!root || !rootR) return [];

  return [...root.querySelectorAll(selector)].map((btn, index) => {
    const r = btn.getBoundingClientRect();
    const text = (btn.textContent || '').trim().slice(0, 24);
    const clippedTop = r.top < rootR.top - 1;
    const clippedBottom = r.bottom > rootR.bottom + 1;
    return {
      index,
      text,
      visible: r.width > 0 && r.height > 0 && !clippedTop && !clippedBottom,
      clippedTop,
      clippedBottom,
      top: Math.round(r.top),
      bottom: Math.round(r.bottom),
    };
  });
}

export function probeLobbySetup(trigger, extra = {}) {
  if (typeof window === 'undefined') return;

  const lobbyLeft = document.querySelector('.lobby-left');
  const lobbyInner = document.querySelector('.lobby-left-inner');
  const picker = document.querySelector('.game-setup-picker');
  const lobbyButtons = document.querySelector('.lobby-buttons');

  const payload = {
    sessionId: '97ed31',
    hypothesisId: 'H1-H5',
    location: 'lobbySetupProbe.js',
    message: 'lobby setup probe',
    data: {
      trigger,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      showSetup: Boolean(picker),
      pickerMode: extra.pickerMode ?? null,
      aiOnly: extra.aiOnly ?? null,
      lobbyLeft: rectSummary(lobbyLeft),
      lobbyInner: rectSummary(lobbyInner),
      picker: rectSummary(picker),
      innerClipped: lobbyInner ? lobbyInner.scrollHeight > lobbyInner.clientHeight + 2 : null,
      pickerClipped: picker ? picker.scrollHeight > picker.clientHeight + 2 : null,
      actionCards: buttonVisibility(lobbyButtons, '.action-card'),
      timerPresets: buttonVisibility(picker, '.btn-timer-preset'),
      colorPicks: buttonVisibility(picker, '.btn-color-pick'),
      createCancel: buttonVisibility(picker, '.btn-setup-create, .btn-timer-cancel'),
      runId: extra.runId ?? 'pre-fix',
      ...extra,
    },
    timestamp: Date.now(),
  };

  // #region agent log
  fetch('http://127.0.0.1:7570/ingest/7c8a0073-ab4a-4548-b425-fe00951377e1', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '97ed31' },
    body: JSON.stringify(payload),
  }).catch(() => {});
  // #endregion
}
