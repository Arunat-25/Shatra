import { test, expect } from '@playwright/test';
import {
  startPvpGame,
  endPvpGameByResign,
  endPvpGameForRematch,
  makeBoardMove,
  pickPlayAsWhite,
  waitForGameBoard,
  visibleGameOverBars,
  visibleOpponentDisconnectBanner,
  clickRematch,
} from './helpers.js';

const WHITE_OPENING = { from: 45, to: 37 };
const MOBILE = { width: 390, height: 844 };

async function startPrivatePvpGame(hostPage, guestPage) {
  await hostPage.goto('/');
  await hostPage.getByRole('button', { name: /друг|friend|private|чакыр/i }).click();
  await pickPlayAsWhite(hostPage);
  await hostPage.locator('.btn-setup-create').click();
  await expect(hostPage).toHaveURL(/\/[a-f0-9-]+(?:\?|$)/);
  const roomId = new URL(hostPage.url()).pathname.slice(1);
  await guestPage.goto(`/${roomId}`);
  await waitForGameBoard(hostPage);
  await waitForGameBoard(guestPage);
  return roomId;
}

test.describe('disconnect and reconnect', () => {
  test('host sees opponent disconnect when guest closes connection', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage, { requireChat: false });
    // setOffline does not tear down an open WebSocket — close the tab to simulate disconnect.
    await guestPage.close();

    await expect(visibleOpponentDisconnectBanner(hostPage)).toBeVisible({ timeout: 15_000 });

    await guestContext.close();
    await hostContext.close();
  });

  test('guest reconnect clears opponent disconnect banner on host', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    let guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage, { requireChat: false });
    const roomUrl = hostPage.url();
    await guestPage.close();
    await expect(visibleOpponentDisconnectBanner(hostPage)).toBeVisible({ timeout: 15_000 });

    guestPage = await guestContext.newPage();
    await guestPage.goto(roomUrl);
    await expect(visibleOpponentDisconnectBanner(hostPage)).toHaveCount(0, { timeout: 20_000 });

    await guestContext.close();
    await hostContext.close();
  });

  test('disconnect countdown decrements on host UI', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage, { requireChat: false });
    await guestPage.close();

    const banner = visibleOpponentDisconnectBanner(hostPage).first();
    await expect(banner).toBeVisible({ timeout: 15_000 });
    const first = Number(await banner.locator('.opponent-disconnect-status__number').textContent());
    await hostPage.waitForTimeout(2500);
    const second = Number(await banner.locator('.opponent-disconnect-status__number').textContent());
    expect(second).toBeLessThan(first);

    await hostContext.close();
    await guestContext.close();
  });
});

test.describe('private room', () => {
  test('private PvP: guest joins and first move syncs', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPrivatePvpGame(hostPage, guestPage);
    await makeBoardMove(hostPage, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');
    await expect.poll(async () => {
      const lines = await guestPage.locator('.move-history-line').allTextContents();
      return lines.some((line) => line.includes('45-37'));
    }, { timeout: 20_000 }).toBe(true);

    await hostContext.close();
    await guestContext.close();
  });
});

test.describe('mobile edge cases', () => {
  test('cancel before first move on mobile viewport', async ({ browser }) => {
    const hostContext = await browser.newContext({ viewport: MOBILE });
    const guestContext = await browser.newContext({ viewport: MOBILE });
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage, { requireChat: false });
    await endPvpGameForRematch(hostPage);

    await expect.poll(async () => (
      await visibleGameOverBars(guestPage).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);

    await hostContext.close();
    await guestContext.close();
  });
});

test.describe('rematch edge cases', () => {
  test('opponent leaving during rematch wait disables rematch for host', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage, { requireChat: false });
    await endPvpGameByResign(hostPage);
    await expect.poll(async () => (
      await visibleGameOverBars(guestPage).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);

    await clickRematch(hostPage);
    await guestPage.close();

    const rematchBtn = hostPage.locator('.game-result-btn--rematch').filter({ visible: true });
    await expect(rematchBtn).toBeDisabled({ timeout: 15_000 });
    await expect(hostPage.locator('.message-warning').filter({ hasText: /реванш отменён|rematch cancelled/i })).toBeVisible();

    await hostContext.close();
    await guestContext.close();
  });

  test('resign then rematch on guest side also works', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage, { requireChat: false });
    await endPvpGameByResign(hostPage);
    await expect.poll(async () => (
      await visibleGameOverBars(guestPage).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);

    const rematchBtn = guestPage.locator('.game-result-btn--rematch').filter({ visible: true });
    await expect(rematchBtn).toBeEnabled({ timeout: 10_000 });
    await rematchBtn.click({ force: true });

    await hostContext.close();
    await guestContext.close();
  });
});
