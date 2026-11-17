import { test, expect } from '@playwright/test';
import {
  startPvpGame,
  endPvpGameByResign,
  makeBoardMove,
  startAiGame,
  waitForGameBoard,
  visibleGameOverBars,
} from './helpers.js';
import { setLiteUi, toggleLiteBoard } from './boardLayoutHelpers.js';

const WHITE_OPENING = { from: 45, to: 37 };

test.describe('draw agreement', () => {
  test('accepting draw ends game for both players', async ({ browser }) => {
    test.setTimeout(90_000);
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);
    await makeBoardMove(hostPage, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');

    await hostPage.getByRole('button', { name: /ничью|draw/i }).click({ force: true });
    const acceptBtn = guestPage.getByRole('button', { name: /принять ничью|accept draw/i });
    await expect(acceptBtn).toBeVisible({ timeout: 15_000 });
    await acceptBtn.click({ force: true });

    await expect.poll(async () => (
      await visibleGameOverBars(hostPage).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);
    await expect.poll(async () => (
      await visibleGameOverBars(guestPage).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);

    await hostContext.close();
    await guestContext.close();
  });

  test('declining draw clears incoming offer UI', async ({ browser }) => {
    test.setTimeout(90_000);
    const hostContext = await browser.newContext();
    const guestContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const guestPage = await guestContext.newPage();

    await startPvpGame(hostPage, guestPage);
    await makeBoardMove(hostPage, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');

    await hostPage.getByRole('button', { name: /ничью|draw/i }).click({ force: true });
    const declineBtn = guestPage.getByRole('button', { name: /отклонить ничью|decline draw/i });
    await expect(declineBtn).toBeVisible({ timeout: 10_000 });
    await declineBtn.click({ force: true });

    await expect(guestPage.getByRole('button', { name: /принять ничью|accept draw/i })).toHaveCount(0, {
      timeout: 10_000,
    });
    await expect(hostPage.getByRole('button', { name: /ничью|draw/i })).toBeEnabled();

    await hostContext.close();
    await guestContext.close();
  });
});

test.describe('AI controls', () => {
  test('resign ends AI game', async ({ page }) => {
    await startAiGame(page, { asWhite: true });
    await endPvpGameByResign(page);
    await expect.poll(async () => (
      await visibleGameOverBars(page).count()
    ), { timeout: 20_000 }).toBeGreaterThan(0);
  });
});

test.describe('lite toggle in game', () => {
  test('toggle lite during AI game keeps board interactive', async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 900 });
    await setLiteUi(page, false);
    await startAiGame(page, { asWhite: true });
    await waitForGameBoard(page);

    await toggleLiteBoard(page);
    await expect(page.locator('.board-canvas, .room-board .kletka').first()).toBeVisible();

    await makeBoardMove(page, WHITE_OPENING.from, WHITE_OPENING.to, 'белый');
    await expect.poll(async () => {
      const lines = await page.locator('.move-history-line').allTextContents();
      return lines.some((line) => line.includes('45-37'));
    }, { timeout: 20_000 }).toBe(true);
  });
});
