import { test, expect } from '@playwright/test';
import {
  assertBoardLayout,
  compareBoardSnapshots,
} from '../src/board/boardLayoutGeometry.js';
import {
  readBoardLayout,
  setLiteUi,
} from './boardLayoutHelpers.js';

const MOBILE_VIEWPORT = { width: 390, height: 760 };
const SHORT_MOBILE_VIEWPORT = { width: 390, height: 700 };

function expectLayoutProfile(snapshot, profile) {
  const result = assertBoardLayout(snapshot, profile);
  expect(result.errors, result.errors.join('; ')).toEqual([]);
}

async function openTutorialLesson(page, section = 1) {
  await page.goto(`/tutorial/${section}`);
  await expect(page.locator('.tutorial-lesson')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('.tutorial-lesson .room-board .board')).toBeVisible();
  await page.waitForTimeout(200);
}

test.describe('tutorial board layout', () => {
  test('mobile regular tutorial board fits stage and shows fortresses', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setLiteUi(page, false);
    await openTutorialLesson(page, 1);

    const snapshot = await readBoardLayout(page);
    expect(snapshot).not.toBeNull();
    expect(snapshot.mode.isCompact).toBe(true);
    expect(snapshot.mode.isLite).toBe(false);
    expectLayoutProfile(snapshot, 'tutorial-mobile-regular');
    expect(await page.locator('.board-canvas').count()).toBe(0);

    const stageOverflow = await page.evaluate(() => {
      const stage = document.querySelector('.tutorial-lesson__stage');
      const board = document.querySelector('.tutorial-lesson .board');
      if (!stage || !board) return true;
      const stageR = stage.getBoundingClientRect();
      const boardR = board.getBoundingClientRect();
      return boardR.bottom > stageR.bottom + 1 || boardR.top < stageR.top - 1;
    });
    expect(stageOverflow).toBe(false);
  });

  test('short mobile viewport keeps tutorial fortresses visible', async ({ page }) => {
    await page.setViewportSize(SHORT_MOBILE_VIEWPORT);
    await setLiteUi(page, false);
    await openTutorialLesson(page, 1);

    const stats = await page.evaluate(() => {
      const slot = document.querySelector('.room-board');
      const board = document.querySelector('.room-board .board');
      const stage = document.querySelector('.tutorial-lesson__stage');
      const slotR = slot.getBoundingClientRect();
      const boardR = board.getBoundingClientRect();
      const stageR = stage.getBoundingClientRect();
      const reserves = [...document.querySelectorAll('.field-of-reserve .kletka')];
      const top = reserves[0];
      const bottom = reserves[reserves.length - 1];
      return {
        boardOverflowsSlot: boardR.height > slotR.height + 2 || boardR.width > slotR.width + 2,
        stageOverflow: boardR.bottom > stageR.bottom + 1 || boardR.top < stageR.top - 1,
        fortTop: top.getBoundingClientRect().top >= slotR.top - 1,
        fortBottom: bottom.getBoundingClientRect().bottom <= slotR.bottom + 1,
      };
    });

    expect(stats.boardOverflowsSlot).toBe(false);
    expect(stats.stageOverflow).toBe(false);
    expect(stats.fortTop).toBe(true);
    expect(stats.fortBottom).toBe(true);
  });

  test('mobile lite tutorial board layout', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setLiteUi(page, true);
    await openTutorialLesson(page, 1);

    const snapshot = await readBoardLayout(page);
    expect(snapshot).not.toBeNull();
    expect(snapshot.mode.isLite).toBe(true);
    expect(snapshot.mode.isCanvas).toBe(true);
    expectLayoutProfile(snapshot, 'tutorial-mobile-lite');
    await expect(page.locator('.board--lite')).toBeVisible();
    await expect(page.locator('.board-canvas')).toBeVisible();
  });

  test('tutorial mobile lite matches regular board slot size', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setLiteUi(page, false);
    await openTutorialLesson(page, 1);

    const regular = await readBoardLayout(page);
    expectLayoutProfile(regular, 'tutorial-mobile-regular');

    await setLiteUi(page, true);
    await page.reload();
    await openTutorialLesson(page, 1);

    const lite = await readBoardLayout(page);
    expectLayoutProfile(lite, 'tutorial-mobile-lite');

    const parity = compareBoardSnapshots(regular, lite);
    expect(parity.diffs, parity.diffs.join('; ')).toEqual([]);
  });
});
