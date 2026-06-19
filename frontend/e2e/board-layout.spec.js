import { test, expect } from '@playwright/test';
import {
  assertBoardLayout,
  compareBoardSnapshots,
} from '../src/board/boardLayoutGeometry.js';
import { startAiGame } from './helpers.js';
import {
  readBoardLayout,
  setLiteUi,
  toggleLiteBoard,
} from './boardLayoutHelpers.js';

const DESKTOP_VIEWPORT = { width: 1400, height: 900 };
const MOBILE_VIEWPORT = { width: 390, height: 760 };

function expectLayoutProfile(snapshot, profile) {
  const result = assertBoardLayout(snapshot, profile);
  expect(result.errors, result.errors.join('; ')).toEqual([]);
}

test.describe('board layout profiles', () => {
  test('desktop regular board layout', async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setLiteUi(page, false);
    await startAiGame(page);
    const snapshot = await readBoardLayout(page);
    expect(snapshot).not.toBeNull();
    expect(snapshot.mode.isLite).toBe(false);
    expect(snapshot.mode.isCanvas).toBe(false);
    expectLayoutProfile(snapshot, 'desktop-regular');
    expect(await page.locator('.board-canvas').count()).toBe(0);
    expect(await page.locator('.room-board .kletka').count()).toBeGreaterThan(0);
  });

  test('desktop lite board layout', async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setLiteUi(page, true);
    await startAiGame(page);
    const snapshot = await readBoardLayout(page);
    expect(snapshot).not.toBeNull();
    expect(snapshot.mode.isLite).toBe(true);
    expect(snapshot.mode.isCanvas).toBe(true);
    expectLayoutProfile(snapshot, 'desktop-lite');
    await expect(page.locator('.board--lite')).toBeVisible();
    await expect(page.locator('.board-canvas')).toBeVisible();
  });

  test('mobile regular board layout', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setLiteUi(page, false);
    await startAiGame(page);
    const snapshot = await readBoardLayout(page);
    expect(snapshot).not.toBeNull();
    expect(snapshot.mode.isCompact).toBe(true);
    expect(snapshot.mode.isLite).toBe(false);
    expectLayoutProfile(snapshot, 'mobile-regular');
    expect(await page.locator('.board-canvas').count()).toBe(0);
  });

  test('mobile lite board layout', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setLiteUi(page, true);
    await startAiGame(page);
    const snapshot = await readBoardLayout(page);
    expect(snapshot).not.toBeNull();
    expect(snapshot.mode.isCompact).toBe(true);
    expect(snapshot.mode.isLite).toBe(true);
    expect(snapshot.mode.isCanvas).toBe(true);
    expectLayoutProfile(snapshot, 'mobile-lite');
    await expect(page.locator('.board--lite')).toBeVisible();
    await expect(page.locator('.board-canvas')).toBeVisible();
  });
});

test.describe('lite ↔ regular parity', () => {
  test('desktop lite matches regular after toggle', async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setLiteUi(page, false);
    await startAiGame(page);

    const regular = await readBoardLayout(page);
    expect(regular.mode.isLite).toBe(false);
    expectLayoutProfile(regular, 'desktop-regular');

    await toggleLiteBoard(page);

    const lite = await readBoardLayout(page);
    expect(lite.mode.isLite).toBe(true);
    expect(lite.mode.isCanvas).toBe(true);
    expectLayoutProfile(lite, 'desktop-lite');

    const parity = compareBoardSnapshots(regular, lite);
    expect(parity.diffs, parity.diffs.join('; ')).toEqual([]);
    await expect(page.locator('.board--lite')).toBeVisible();
    await expect(page.locator('.board-canvas')).toBeVisible();
  });

  test('mobile lite matches regular after toggle', async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setLiteUi(page, false);
    await startAiGame(page);

    const regular = await readBoardLayout(page);
    expect(regular.mode.isLite).toBe(false);
    expectLayoutProfile(regular, 'mobile-regular');

    await toggleLiteBoard(page);

    const lite = await readBoardLayout(page);
    expect(lite.mode.isLite).toBe(true);
    expect(lite.mode.isCanvas).toBe(true);
    expectLayoutProfile(lite, 'mobile-lite');

    const parity = compareBoardSnapshots(regular, lite);
    expect(parity.diffs, parity.diffs.join('; ')).toEqual([]);
    await expect(page.locator('.board--lite')).toBeVisible();
    await expect(page.locator('.board-canvas')).toBeVisible();
  });
});
