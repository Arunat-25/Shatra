import { test, expect } from '@playwright/test';
import { expectChatMessage, sendChatMessage, startPvpGame } from './helpers.js';

test('private invite shows QR code', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: /друг|friend|private|чакыр/i }).click();
  await page.locator('.btn-setup-create').click();

  await expect(page).toHaveURL(/\/[a-f0-9]{8}$/);
  await expect(page).not.toHaveURL(/mode=private/);
  await expect(page.locator('.waiting-qr')).toBeVisible({ timeout: 15_000 });
  await expect(page.locator('.waiting-link-url')).toBeVisible();
  await expect(page.locator('.waiting-link-url')).not.toContainText('mode=private');
});

test('PvP chat: guest sees host message', async ({ browser }) => {
  const hostContext = await browser.newContext();
  const guestContext = await browser.newContext();
  const hostPage = await hostContext.newPage();
  const guestPage = await guestContext.newPage();

  await startPvpGame(hostPage, guestPage);

  await sendChatMessage(hostPage, 'playwright hello');
  await expectChatMessage(hostPage, 'playwright hello');
  await expectChatMessage(guestPage, 'playwright hello');

  await hostPage.getByRole('button', { name: /скрыть|hide/i }).click();
  await sendChatMessage(guestPage, 'hidden from host');

  await expect(hostPage.locator('.game-chat-text', { hasText: 'hidden from host' })).toHaveCount(0);
  await expectChatMessage(guestPage, 'hidden from host');

  await hostContext.close();
  await guestContext.close();
});
