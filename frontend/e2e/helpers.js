import { expect } from '@playwright/test';

/** Дождаться старта партии: зал ожидания скрыт, видна клетка основного поля. */
export async function waitForGameBoard(page, { timeout = 60_000 } = {}) {
  await expect(page.locator('.waiting-screen')).toHaveCount(0, { timeout });
  const cell = page.locator('.room-board .main-field .kletka').first();
  await cell.scrollIntoViewIfNeeded();
  await expect(cell).toBeVisible({ timeout: 15_000 });
  return cell;
}

/** Отправить сообщение в чат PvP (форма в боковой панели). */
export async function sendChatMessage(page, text) {
  const chat = page.locator('.game-chat');
  await expect(chat).toBeVisible();
  const input = chat.getByRole('textbox');
  await input.fill(text);
  const sendBtn = chat.getByRole('button', { name: /отпр|send/i });
  await expect(sendBtn).toBeEnabled({ timeout: 5000 });
  await sendBtn.click();
}

/** Дождаться текста в ленте чата. */
export async function expectChatMessage(page, text, { timeout = 15_000 } = {}) {
  await expect(page.locator('.game-chat-text', { hasText: text })).toBeVisible({ timeout });
}
