/** Debug probe: mobile board slot vs content geometry (session 97ed31). */
export function probeBoardLayout(trigger, extra = {}) {
  if (typeof window === 'undefined') return;

  const slot = document.querySelector('.room-board');
  const board = document.querySelector('.room-board .board');
  const content = document.querySelector('.room-board .board-content');
  if (!slot || !board) return;

  const slotR = slot.getBoundingClientRect();
  const boardR = board.getBoundingClientRect();
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

  const payload = {
    sessionId: '97ed31',
    hypothesisId: 'H1-H5',
    location: 'boardLayoutProbe.js',
    message: 'board layout probe',
    data: {
      trigger,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      slotClient: `${slot.clientWidth}x${slot.clientHeight}`,
      slotCqw: slotCs.getPropertyValue('container-type'),
      boardClient: `${board.clientWidth}x${board.clientHeight}`,
      boardScroll: `${board.scrollWidth}x${board.scrollHeight}`,
      contentScrollH: content?.scrollHeight ?? null,
      clippedVertical: board.scrollHeight > slot.clientHeight + 2,
      boardOverflowsSlot:
        boardR.height > slotR.height + 2 || boardR.width > slotR.width + 2,
      fortTopVisible,
      fortBottomVisible,
      boardUnit: cs.getPropertyValue('--board-unit').trim(),
      boardWidth: cs.width,
      boardClasses: board.className,
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
