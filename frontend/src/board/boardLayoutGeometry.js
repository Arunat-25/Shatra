/** @typedef {{ x: number, y: number, width: number, height: number }} Rect */

export const TOLERANCE_PX = 2;
export const COMPACT_MAX_WIDTH = 1319;
export const DESKTOP_BOARD_PADDING_PX = 14;

/**
 * @param {DOMRect | { x: number, y: number, width: number, height: number } | null | undefined} rect
 * @returns {Rect | null}
 */
export function rectFromDomRect(rect) {
  if (!rect) return null;
  return {
    x: rect.x,
    y: rect.y,
    width: rect.width,
    height: rect.height,
  };
}

/**
 * @param {Document | DocumentFragment} doc
 * @returns {import('./boardLayoutGeometry.js').BoardLayoutSnapshot | null}
 */
export function readBoardLayoutSnapshot(doc = document) {
  if (typeof doc?.querySelector !== 'function') return null;

  const slot = doc.querySelector('.room-board');
  const board = doc.querySelector('.room-board .board');
  const content = doc.querySelector('.room-board .board-content');
  const topBar = doc.querySelector('.game-player-bar--top');
  const bottomBar = doc.querySelector('.game-player-bar--bottom');
  const canvas = doc.querySelector('.board-canvas');
  if (!slot || !board) return null;

  const slotR = slot.getBoundingClientRect();
  const boardR = board.getBoundingClientRect();
  const contentR = content?.getBoundingClientRect();
  const canvasR = canvas?.getBoundingClientRect();
  const topBarR = topBar?.getBoundingClientRect();
  const bottomBarR = bottomBar?.getBoundingClientRect();
  const reserveTop = doc.querySelector('.field-of-reserve .kletka');
  const reserveCells = [...doc.querySelectorAll('.field-of-reserve .kletka')];
  const reserveBottom = reserveCells[reserveCells.length - 1] ?? null;
  const cs = typeof getComputedStyle === 'function' ? getComputedStyle(board) : null;

  const fortTopVisible = reserveTop
    ? reserveTop.getBoundingClientRect().top >= slotR.top - 1
    : null;
  const fortBottomVisible = reserveBottom
    ? reserveBottom.getBoundingClientRect().bottom <= slotR.bottom + 1
    : null;
  const overlapsTopBar = topBarR
    ? boardR.top < topBarR.bottom - 1
    : null;
  const topBarVisible = topBar && cs
    ? getComputedStyle(topBar).display !== 'none'
    : false;
  const bottomBarVisible = bottomBar && cs
    ? getComputedStyle(bottomBar).display !== 'none'
    : false;

  const viewportWidth = typeof window !== 'undefined' ? window.innerWidth : 0;
  const viewportHeight = typeof window !== 'undefined' ? window.innerHeight : 0;
  const isCanvas = Boolean(canvas);
  const isLite = board.classList.contains('board--lite');

  return {
    viewport: { width: viewportWidth, height: viewportHeight },
    mode: {
      isLite,
      isCanvas,
      isCompact: viewportWidth > 0 && viewportWidth <= COMPACT_MAX_WIDTH,
    },
    slot: rectFromDomRect(slotR),
    board: rectFromDomRect(boardR),
    content: rectFromDomRect(contentR),
    canvas: rectFromDomRect(canvasR),
    topBar: rectFromDomRect(topBarR),
    bottomBar: rectFromDomRect(bottomBarR),
    gapBelowTopBar: topBarVisible && topBarR ? Math.round(boardR.top - topBarR.bottom) : null,
    gapAboveBottomBar: bottomBarVisible && bottomBarR ? Math.round(bottomBarR.top - boardR.bottom) : null,
    contentInsetTop: contentR ? Math.round(contentR.top - boardR.top) : null,
    contentInsetBottom: contentR ? Math.round(boardR.bottom - contentR.bottom) : null,
    boardOverflowsSlot:
      boardR.height > slotR.height + TOLERANCE_PX || boardR.width > slotR.width + TOLERANCE_PX,
    contentOverflowsBoard: contentR
      ? contentR.height > boardR.height + TOLERANCE_PX || contentR.width > boardR.width + TOLERANCE_PX
      : null,
    overlapsTopBar: topBarVisible ? overlapsTopBar : null,
    fortTopVisible,
    fortBottomVisible,
    boardUnit: cs?.getPropertyValue('--board-unit').trim() ?? '',
    heightUnits: cs?.getPropertyValue('--board-height-units').trim() ?? '',
    paddingTop: cs ? parseFloat(cs.paddingTop) : null,
    paddingBottom: cs ? parseFloat(cs.paddingBottom) : null,
    boardFlexShrink: cs?.flexShrink ?? null,
  };
}

/**
 * @param {number | null | undefined} a
 * @param {number | null | undefined} b
 * @param {number} tolerancePx
 */
export function withinTolerance(a, b, tolerancePx = TOLERANCE_PX) {
  if (a == null || b == null) return a === b;
  return Math.abs(a - b) <= tolerancePx;
}

/**
 * @param {Rect | null} a
 * @param {Rect | null} b
 * @param {number} tolerancePx
 */
export function rectsMatch(a, b, tolerancePx = TOLERANCE_PX) {
  if (!a || !b) return a === b;
  return (
    withinTolerance(a.x, b.x, tolerancePx)
    && withinTolerance(a.y, b.y, tolerancePx)
    && withinTolerance(a.width, b.width, tolerancePx)
    && withinTolerance(a.height, b.height, tolerancePx)
  );
}

/**
 * @param {ReturnType<typeof readBoardLayoutSnapshot>} a
 * @param {ReturnType<typeof readBoardLayoutSnapshot>} b
 * @param {{ tolerancePx?: number }} [opts]
 */
export function compareBoardSnapshots(a, b, opts = {}) {
  const tolerancePx = opts.tolerancePx ?? TOLERANCE_PX;
  if (!a || !b) {
    return { ok: false, diffs: ['missing snapshot'] };
  }

  const diffs = [];
  const check = (label, va, vb) => {
    if (!withinTolerance(va, vb, tolerancePx)) {
      diffs.push(`${label}: ${va} vs ${vb}`);
    }
  };

  if (!rectsMatch(a.board, b.board, tolerancePx)) {
    diffs.push(`board: ${JSON.stringify(a.board)} vs ${JSON.stringify(b.board)}`);
  }

  const aGrid = a.canvas ?? a.content;
  const bGrid = b.canvas ?? b.content;
  if (!rectsMatch(aGrid, bGrid, tolerancePx)) {
    diffs.push(`grid: ${JSON.stringify(aGrid)} vs ${JSON.stringify(bGrid)}`);
  }

  check('gapBelowTopBar', a.gapBelowTopBar, b.gapBelowTopBar);
  check('gapAboveBottomBar', a.gapAboveBottomBar, b.gapAboveBottomBar);
  check('contentInsetTop', a.contentInsetTop, b.contentInsetTop);
  check('contentInsetBottom', a.contentInsetBottom, b.contentInsetBottom);

  return { ok: diffs.length === 0, diffs };
}

/**
 * @param {number | null | undefined} value
 * @param {number} expected
 * @param {number} tolerancePx
 * @param {string} label
 * @param {string[]} errors
 */
function expectNear(value, expected, tolerancePx, label, errors) {
  if (value == null) {
    errors.push(`${label}: missing`);
    return;
  }
  if (!withinTolerance(value, expected, tolerancePx)) {
    errors.push(`${label}: expected ~${expected}, got ${value}`);
  }
}

/**
 * @param {ReturnType<typeof readBoardLayoutSnapshot>} snapshot
 * @param {
 *   'desktop-regular' | 'desktop-lite' | 'mobile-regular' | 'mobile-lite'
 *   | 'tutorial-mobile-regular' | 'tutorial-mobile-lite'
 * } profile
 * @returns {{ ok: boolean, errors: string[] }}
 */
export function assertBoardLayout(snapshot, profile) {
  const errors = [];
  if (!snapshot) {
    return { ok: false, errors: ['no snapshot'] };
  }

  const isTutorial = profile.startsWith('tutorial-');
  const baseProfile = isTutorial ? profile.slice('tutorial-'.length) : profile;
  const [viewportKind, boardKind] = baseProfile.split('-');
  const isDesktop = viewportKind === 'desktop';
  const isLite = boardKind === 'lite';

  if (snapshot.mode.isCompact === isDesktop) {
    errors.push(`viewport: expected ${viewportKind}, got compact=${snapshot.mode.isCompact}`);
  }
  if (snapshot.mode.isLite !== isLite) {
    errors.push(`board kind: expected lite=${isLite}, got lite=${snapshot.mode.isLite}`);
  }
  if (isLite !== snapshot.mode.isCanvas) {
    errors.push(`canvas: expected ${isLite}, got ${snapshot.mode.isCanvas}`);
  }
  if (!isLite && snapshot.mode.isCanvas) {
    errors.push('regular board must not use canvas');
  }

  if (!isTutorial && snapshot.overlapsTopBar) {
    errors.push('board overlaps top player bar');
  }

  if (snapshot.mode.isCompact && !isTutorial) {
    expectNear(snapshot.gapBelowTopBar, 0, TOLERANCE_PX, 'gapBelowTopBar', errors);
    expectNear(snapshot.gapAboveBottomBar, 0, TOLERANCE_PX, 'gapAboveBottomBar', errors);
  }

  if (snapshot.boardOverflowsSlot) {
    errors.push('board overflows slot');
  }
  if (snapshot.contentOverflowsBoard) {
    errors.push('content overflows board');
  }

  if (isDesktop) {
    expectNear(
      snapshot.contentInsetTop,
      DESKTOP_BOARD_PADDING_PX,
      TOLERANCE_PX,
      'contentInsetTop',
      errors,
    );
    expectNear(
      snapshot.contentInsetBottom,
      DESKTOP_BOARD_PADDING_PX,
      TOLERANCE_PX,
      'contentInsetBottom',
      errors,
    );
  } else {
    expectNear(snapshot.contentInsetTop, 0, TOLERANCE_PX, 'contentInsetTop', errors);
    expectNear(snapshot.contentInsetBottom, 0, TOLERANCE_PX, 'contentInsetBottom', errors);
  }

  if (!isLite) {
    if (snapshot.fortTopVisible !== true) {
      errors.push('top fortress not visible in slot');
    }
    if (snapshot.fortBottomVisible !== true) {
      errors.push('bottom fortress not visible in slot');
    }
  }

  if (snapshot.mode.isCompact && !isLite && snapshot.heightUnits && snapshot.heightUnits !== '13.16') {
    errors.push(`mobile heightUnits: expected 13.16, got ${snapshot.heightUnits}`);
  }

  return { ok: errors.length === 0, errors };
}
