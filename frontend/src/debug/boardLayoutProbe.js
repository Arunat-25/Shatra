import { readBoardLayoutSnapshot } from '../board/boardLayoutGeometry';
import { sendDevProbe } from './devProbe';

/** Debug probe: board slot vs content geometry (overflow check). Dev only. */
export function probeBoardLayout(trigger, extra = {}) {
  if (typeof window === 'undefined') return;

  const snapshot = readBoardLayoutSnapshot(document);
  if (!snapshot) return snapshot;

  sendDevProbe({
    sessionId: 'dev',
    hypothesisId: 'layout',
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
      ...extra,
    },
  });

  return snapshot;
}
