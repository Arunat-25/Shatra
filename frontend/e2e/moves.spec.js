import { test, expect } from '@playwright/test';
import {
  expectMoveHistoryContains,
  makeBoardMove,
  startAiGame,
  startPvpGame,
} from './helpers.js';

/** Легальный дебют белых (tests/test_ai.py). */
const WHITE_OPENING = { from: 45, to: 37 };
const BLACK_REPLY = { from: 23, to: 29 };

test.describe('game room moves', () => {
  test('AI game (desktop): white plays 45-37 and move appears in history', async ({ page }) => {
    await startAiGame(page, { asWhite: true });
    await makeBoardMove(page, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');
    await expectMoveHistoryContains(page, '45-37');
    await expect(page.locator('.move-history-line', { hasText: '45-37' })).not.toHaveCount(0);
  });

  async function expectBoardCellsSized(page, minHeight = 20) {
    await expect.poll(async () => page.evaluate(() => {
      const heights = [...document.querySelectorAll('.room-board .kletka')]
        .map((c) => c.getBoundingClientRect().height);
      return heights.length ? Math.min(...heights) : 0;
    }), { message: 'Board cells collapsed to zero height' }).toBeGreaterThan(minHeight);
  }

  test('AI game (mobile): white plays 45-37 and board stays visible', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await startAiGame(page, { asWhite: true });
    await expect(page.locator('.room-board .kletka').first()).toBeVisible();
    await makeBoardMove(page, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');
    await expectBoardCellsSized(page);
    await expectMoveHistoryContains(page, '45-37');
    const boxAfterMove = await page.locator('.room-board .board').boundingBox();
    expect(boxAfterMove?.height ?? 0).toBeGreaterThan(80);
    await expect(page.locator('.game-viewport-below-fold')).toBeVisible();
  });

  test('PvP (mobile): host move visible to guest', async ({ browser }) => {
    const viewport = { width: 390, height: 844 };
    const hostContext = await browser.newContext({ viewport });
    const guestContext = await browser.newContext({ viewport });
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);

    await expect(hostPage.locator('.room-board .kletka').first()).toBeVisible();
    await expect(guestPage.locator('.room-board .kletka').first()).toBeVisible();

    await makeBoardMove(hostPage, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');
    await expectMoveHistoryContains(hostPage, '45-37');
    await expectMoveHistoryContains(guestPage, '45-37');

    await hostContext.close();
    await guestContext.close();
  });

  test('PvP: host move visible to both players', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);

    await makeBoardMove(hostPage, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');
    await expectMoveHistoryContains(hostPage, '45-37');
    await expectMoveHistoryContains(guestPage, '45-37');

    await hostContext.close();
    await guestContext.close();
  });

  test('PvP: guest replies 23-29 after host opening', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);

    await makeBoardMove(hostPage, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');
    await expectMoveHistoryContains(guestPage, '45-37');

    await makeBoardMove(guestPage, BLACK_REPLY.from, BLACK_REPLY.to, 'черный');
    await expectMoveHistoryContains(hostPage, '23-29');
    await expectMoveHistoryContains(guestPage, '23-29');

    await hostContext.close();
    await guestContext.close();
  });
});
