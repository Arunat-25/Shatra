import { test, expect } from '@playwright/test';
import {
  expectLobbyChatMessage,
  sendLobbyChatMessage,
} from './helpers.js';

test('lobby layout shows three columns on desktop', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.lobby-layout')).toBeVisible();
  await expect(page.locator('.lobby-left')).toBeVisible();
  await expect(page.locator('.lobby-right')).toBeVisible();
  await expect(page.locator('.lobby-chat')).toBeVisible();
});

test('lobby chat: sender sees own message', async ({ page }) => {
  await page.goto('/');
  const text = `lobby-e2e-${Date.now()}`;
  await sendLobbyChatMessage(page, text);
  await expectLobbyChatMessage(page, text);
});

test('lobby chat: second browser sees first user message', async ({ browser }) => {
  const text = `lobby-sync-${Date.now()}`;
  const ctxA = await browser.newContext();
  const ctxB = await browser.newContext();
  const pageA = await ctxA.newPage();
  const pageB = await ctxB.newPage();

  await pageA.goto('/');
  await pageB.goto('/');
  await sendLobbyChatMessage(pageA, text);
  await expectLobbyChatMessage(pageA, text);
  await expectLobbyChatMessage(pageB, text, { timeout: 20_000 });

  await ctxA.close();
  await ctxB.close();
});

test('lobby chat: rapid second send shows cooldown error', async ({ page }) => {
  await page.goto('/');
  await sendLobbyChatMessage(page, 'first-msg');
  await expectLobbyChatMessage(page, 'first-msg');
  await sendLobbyChatMessage(page, 'second-too-fast');
  await expect(page.locator('.lobby-chat-error')).toBeVisible({ timeout: 5000 });
});

test('lobby chat: reload shows recent history', async ({ page }) => {
  const text = `lobby-history-${Date.now()}`;
  await page.goto('/');
  await sendLobbyChatMessage(page, text);
  await expectLobbyChatMessage(page, text);
  await page.reload();
  await expectLobbyChatMessage(page, text, { timeout: 20_000 });
});

test('lobby chat input respects 500 character max', async ({ page }) => {
  await page.goto('/');
  const input = page.locator('.lobby-chat').getByRole('textbox');
  await expect(input).toHaveAttribute('maxlength', '500');
});
