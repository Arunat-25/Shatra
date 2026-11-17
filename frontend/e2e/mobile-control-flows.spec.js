import { test, expect } from '@playwright/test';
import {
  startPvpGame,
  endPvpGameByResign,
  waitForGameBoard,
  visibleGameOverBars,
} from './helpers.js';

const MOBILE = { width: 390, height: 844 };

test.describe('mobile PvP controls', () => {
  test('resign from host ends game on compact viewport', async ({ browser }) => {
    const hostContext = await browser.newContext({ viewport: MOBILE });
    const guestContext = await browser.newContext({ viewport: MOBILE });
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage, { requireChat: false });
    await waitForGameBoard(hostPage);
    await endPvpGameByResign(hostPage);

    await expect.poll(async () => (
      await visibleGameOverBars(hostPage).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);
    await expect.poll(async () => (
      await visibleGameOverBars(guestPage).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);

    await hostContext.close();
    await guestContext.close();
  });
});
