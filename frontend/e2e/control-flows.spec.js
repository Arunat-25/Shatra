import { test, expect } from '@playwright/test';
import {
  startPvpGame,
  endPvpGameByResign,
  endPvpGameForRematch,
  clickRematch,
  expectActiveGame,
  makeBoardMove,
  waitForGameBoard,
  visibleGameOverBars,
} from './helpers.js';

const WHITE_OPENING = { from: 45, to: 37 };

test.describe('PvP control flows', () => {
  test('cancel before first move ends game for both players', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);
    await endPvpGameForRematch(hostPage);

    await expect.poll(async () => (
      await visibleGameOverBars(guestPage).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);

    await hostContext.close();
    await guestContext.close();
  });

  test('guest resign ends game for host', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);
    await endPvpGameByResign(guestPage);

    await expect.poll(async () => (
      await hostPage.locator('.game-actions-bar--game-over').filter({ visible: true }).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);
    await expect.poll(async () => (
      await guestPage.locator('.game-actions-bar--game-over').filter({ visible: true }).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);

    await hostContext.close();
    await guestContext.close();
  });

  test('draw offer appears for opponent', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);
    await makeBoardMove(hostPage, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');

    const drawBtn = hostPage.getByRole('button', { name: /ничью|draw/i });
    await expect(drawBtn).toBeEnabled();
    await drawBtn.click();

    await expect.poll(async () => (
      await guestPage.getByRole('button', { name: /принять ничью|accept draw/i }).count()
    ), { timeout: 15_000 }).toBeGreaterThan(0);

    await hostContext.close();
    await guestContext.close();
  });

  test('rematch after cancel starts fresh game', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);
    await endPvpGameForRematch(hostPage);
    await expect.poll(async () => (
      await guestPage.locator('.game-actions-bar--game-over').count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);

    await clickRematch(hostPage);
    await clickRematch(guestPage);
    await expectActiveGame(hostPage);
    await expectActiveGame(guestPage);

    await hostContext.close();
    await guestContext.close();
  });

  test('reconnect after move preserves board state', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);
    await makeBoardMove(hostPage, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');

    await hostPage.context().setOffline(true);
    await hostPage.waitForTimeout(1200);
    await hostPage.context().setOffline(false);

    await waitForGameBoard(hostPage, { timeout: 30_000 });
    await expect(hostPage.locator('.game-actions-bar--game-over')).toHaveCount(0);
    await expect.poll(async () => {
      const lines = await hostPage.locator('.move-history-line').allTextContents();
      return lines.some((line) => line.includes('45-37'));
    }, { timeout: 20_000 }).toBe(true);

    await guestContext.close();
    await hostContext.close();
  });
});
