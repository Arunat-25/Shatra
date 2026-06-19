import { expect } from '@playwright/test';
import { LITE_UI_KEY } from '../src/ui/liteUiSettings.js';
import { TOLERANCE_PX } from '../src/board/boardLayoutGeometry.js';

/**
 * Mirror of readBoardLayoutSnapshot for page.evaluate (cannot import ES modules in browser).
 * Keep in sync with frontend/src/board/boardLayoutGeometry.js
 * @returns {import('../src/board/boardLayoutGeometry.js').BoardLayoutSnapshot | null}
 */
function readBoardLayoutSnapshotInBrowser() {
  const tolerancePx = 2;
  const compactMaxWidth = 1319;
  const rectFromDomRect = (rect) => {
    if (!rect) return null;
    return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
  };

  const slot = document.querySelector('.room-board');
  const board = document.querySelector('.room-board .board');
  const content = document.querySelector('.room-board .board-content');
  const topBar = document.querySelector('.game-player-bar--top');
  const bottomBar = document.querySelector('.game-player-bar--bottom');
  const canvas = document.querySelector('.board-canvas');
  if (!slot || !board) return null;

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

  const fortTopVisible = reserveTop
    ? reserveTop.getBoundingClientRect().top >= slotR.top - 1
    : null;
  const fortBottomVisible = reserveBottom
    ? reserveBottom.getBoundingClientRect().bottom <= slotR.bottom + 1
    : null;
  const overlapsTopBar = topBarR ? boardR.top < topBarR.bottom - 1 : null;
  const topBarVisible = topBar ? getComputedStyle(topBar).display !== 'none' : false;
  const bottomBarVisible = bottomBar ? getComputedStyle(bottomBar).display !== 'none' : false;

  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const isCanvas = Boolean(canvas);
  const isLite = board.classList.contains('board--lite');

  return {
    viewport: { width: viewportWidth, height: viewportHeight },
    mode: {
      isLite,
      isCanvas,
      isCompact: viewportWidth > 0 && viewportWidth <= compactMaxWidth,
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
      boardR.height > slotR.height + tolerancePx || boardR.width > slotR.width + tolerancePx,
    contentOverflowsBoard: contentR
      ? contentR.height > boardR.height + tolerancePx || contentR.width > boardR.width + tolerancePx
      : null,
    overlapsTopBar: topBarVisible ? overlapsTopBar : null,
    fortTopVisible,
    fortBottomVisible,
    boardUnit: cs.getPropertyValue('--board-unit').trim(),
    heightUnits: cs.getPropertyValue('--board-height-units').trim(),
    paddingTop: parseFloat(cs.paddingTop),
    paddingBottom: parseFloat(cs.paddingBottom),
    boardFlexShrink: cs.flexShrink,
  };
}

/** Set lite UI preference before navigation. */
export async function setLiteUi(page, enabled) {
  await page.addInitScript(({ key, value }) => {
    localStorage.setItem(key, value);
  }, { key: LITE_UI_KEY, value: enabled ? 'true' : 'false' });
}

/** Read board layout snapshot from the live page. */
export async function readBoardLayout(page) {
  return page.evaluate(readBoardLayoutSnapshotInBrowser);
}

/** Toggle lite board mode and wait for the board surface to switch. */
export async function toggleLiteBoard(page) {
  const wasCanvas = (await page.locator('.board-canvas').count()) > 0;
  let toggle = page.locator('.app-lite-ui-toggle');
  if (!(await toggle.isVisible().catch(() => false))) {
    const menuBtn = page.getByRole('button', { name: /меню|menu/i });
    await menuBtn.click();
    toggle = page.locator('.app-nav-drawer__link').filter({ hasText: /lite board|облегч/i });
  }
  await expect(toggle).toBeVisible();
  await toggle.click();
  if (wasCanvas) {
    await expect(page.locator('.room-board .kletka').first()).toBeVisible({ timeout: 15_000 });
  } else {
    await expect(page.locator('.board-canvas')).toBeVisible({ timeout: 15_000 });
  }
}

export { TOLERANCE_PX };