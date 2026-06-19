/** Debug probe: board slot vs content geometry (overflow check). */
export function probeBoardLayout(trigger, extra = {}) {
  if (typeof window === 'undefined') return;

  const slot = document.querySelector('.room-board');
  const board = document.querySelector('.room-board .board');
  const content = document.querySelector('.room-board .board-content');
  const topBar = document.querySelector('.game-player-bar--top');
  const bottomBar = document.querySelector('.game-player-bar--bottom');
  const canvas = document.querySelector('.board-canvas');
  if (!slot || !board) return;

  const slotR = slot.getBoundingClientRect();
  const boardR = board.getBoundingClientRect();
  const contentR = content?.getBoundingClientRect();
  const canvasR = canvas?.getBoundingClientRect();
  const topBarR = topBar?.getBoundingClientRect();
  const bottomBarR = bottomBar?.getBoundingClientRect();
  const reserveTop = document.querySelector('.field-of-reserve .kletka');
  const reserveCells = [...document.querySelectorAll('.field-of-reserve .kletka')];
  const reserveBottom = reserveCells[reserveCells.length - 1] ?? null;
  const cs = getComputedStyle(board);
  const slotCs = getComputedStyle(slot);

  const fortTopVisible = reserveTop
    ? reserveTop.getBoundingClientRect().top >= slotR.top - 1
    : null;
  const fortBottomVisible = reserveBottom
    ? reserveBottom.getBoundingClientRect().bottom <= slotR.bottom + 1
    : null;
  const overlapsTopBar = topBarR
    ? boardR.top < topBarR.bottom - 1
    : null;
  const gapBelowTopBar = topBarR ? Math.round(boardR.top - topBarR.bottom) : null;
  const gapAboveBottomBar = bottomBarR ? Math.round(bottomBarR.top - boardR.bottom) : null;
  const contentInsetTop = contentR ? Math.round(contentR.top - boardR.top) : null;
  const contentInsetBottom = contentR ? Math.round(boardR.bottom - contentR.bottom) : null;

  const payload = {
    sessionId: 'a9d1b1',
    hypothesisId: 'overflow',
    location: 'boardLayoutProbe.js',
    message: 'board layout probe',
    data: {
      trigger,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      slotClient: `${slot.clientWidth}x${slot.clientHeight}`,
      boardClient: `${board.clientWidth}x${board.clientHeight}`,
      contentClient: content ? `${content.clientWidth}x${content.clientHeight}` : null,
      canvasClient: canvas ? `${canvas.clientWidth}x${canvas.clientHeight}` : null,
      boardOverflowsSlot:
        boardR.height > slotR.height + 2 || boardR.width > slotR.width + 2,
      contentOverflowsBoard: contentR
        ? contentR.height > boardR.height + 2 || contentR.width > boardR.width + 2
        : null,
      overlapsTopBar,
      gapBelowTopBar,
      gapAboveBottomBar,
      contentInsetTop,
      contentInsetBottom,
      fortTopVisible,
      fortBottomVisible,
      boardUnit: cs.getPropertyValue('--board-unit').trim(),
      heightUnits: cs.getPropertyValue('--board-height-units').trim(),
      boardFlexShrink: cs.flexShrink,
      runId: extra.runId ?? 'overflow-fix',
      ...extra,
    },
    timestamp: Date.now(),
  };

  // #region agent log
  fetch('http://127.0.0.1:7570/ingest/7c8a0073-ab4a-4548-b425-fe00951377e1', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'a9d1b1' },
    body: JSON.stringify(payload),
  }).catch(() => {});
  // #endregion
}
