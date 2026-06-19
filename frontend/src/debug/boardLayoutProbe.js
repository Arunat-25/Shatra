import { readBoardLayoutSnapshot } from '../board/boardLayoutGeometry';

/** Debug probe: board slot vs content geometry (overflow check). */
export function probeBoardLayout(trigger, extra = {}) {
  if (typeof window === 'undefined') return;

  const snapshot = readBoardLayoutSnapshot(document);
  if (!snapshot) return;

  const payload = {
    sessionId: 'a9d1b1',
    hypothesisId: 'overflow',
    location: 'boardLayoutProbe.js',
    message: 'board layout probe',
    data: {
      trigger,
      viewport: `${snapshot.viewport.width}x${snapshot.viewport.height}`,
      slotClient: snapshot.slot ? `${snapshot.slot.width}x${snapshot.slot.height}` : null,
      boardClient: snapshot.board ? `${snapshot.board.width}x${snapshot.board.height}` : null,
      contentClient: snapshot.content ? `${snapshot.content.width}x${snapshot.content.height}` : null,
      canvasClient: snapshot.canvas ? `${snapshot.canvas.width}x${snapshot.canvas.height}` : null,
      boardOverflowsSlot: snapshot.boardOverflowsSlot,
      contentOverflowsBoard: snapshot.contentOverflowsBoard,
      overlapsTopBar: snapshot.overlapsTopBar,
      gapBelowTopBar: snapshot.gapBelowTopBar,
      gapAboveBottomBar: snapshot.gapAboveBottomBar,
      contentInsetTop: snapshot.contentInsetTop,
      contentInsetBottom: snapshot.contentInsetBottom,
      fortTopVisible: snapshot.fortTopVisible,
      fortBottomVisible: snapshot.fortBottomVisible,
      boardUnit: snapshot.boardUnit,
      heightUnits: snapshot.heightUnits,
      boardFlexShrink: snapshot.boardFlexShrink,
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
