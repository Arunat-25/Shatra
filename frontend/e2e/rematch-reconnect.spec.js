import { test, expect } from '@playwright/test';
import {
  startPvpGame,
  endPvpGameByResign,
  clickRematch,
  expectActiveGame,
  makeBoardMove,
  startAiGame,
  waitForGameBoard,
  visibleGameOverBars,
} from './helpers.js';

test('PvP rematch starts new game when both players ready', async ({ browser }) => {
  test.setTimeout(120_000);
  const hostContext = await browser.newContext();
  const guestContext = await browser.newContext();
  const hostPage = await hostContext.newPage();
  const guestPage = await guestContext.newPage();

  await startPvpGame(hostPage, guestPage, { requireChat: true });
  await endPvpGameByResign(hostPage);
  await expect.poll(async () => (
    await visibleGameOverBars(hostPage).count()
  ), { timeout: 30_000 }).toBeGreaterThan(0);
  await expect.poll(async () => (
    await visibleGameOverBars(guestPage).count()
  ), { timeout: 30_000 }).toBeGreaterThan(0);

  await clickRematch(hostPage);
  await clickRematch(guestPage);

  await expectActiveGame(hostPage);
  await expectActiveGame(guestPage);

  await hostContext.close();
  await guestContext.close();
});

test('reconnect during active game preserves board (sync resync)', async ({ page }) => {
  await startAiGame(page, { asWhite: true });
  await makeBoardMove(page, 45, 37, 'белый');

  await page.context().setOffline(true);
  await page.waitForTimeout(1500);
  await page.context().setOffline(false);

  await waitForGameBoard(page, { timeout: 30_000 });
  await expect(page.locator('.game-actions-bar--game-over')).toHaveCount(0);
  await expect(page.locator('.waiting-screen')).toHaveCount(0);
});
