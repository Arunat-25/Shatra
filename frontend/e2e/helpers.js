import { expect } from '@playwright/test';

/** Дождаться старта партии: зал ожидания скрыт, видна клетка основного поля. */
export async function waitForGameBoard(page, { timeout = 60_000 } = {}) {
  await expect(page.locator('.waiting-screen')).toHaveCount(0, { timeout });
  const cell = page.locator('.room-board .main-field .kletka').first();
  await cell.scrollIntoViewIfNeeded();
  await expect(cell).toBeVisible({ timeout: 15_000 });
  return cell;
}

/** Чат в игровой комнате (не лобби). */
export function gameChatLocator(page) {
  return page.locator('.room-left .game-chat');
}

/** Дождаться, пока WS подключён и поле чата доступно. */
export async function waitForGameChatReady(page, { timeout = 20_000 } = {}) {
  const chat = gameChatLocator(page);
  await expect(chat).toBeVisible({ timeout });
  await expect(chat.getByRole('textbox')).toBeEnabled({ timeout });
}

/** Отправить сообщение в чат PvP (форма в боковой панели). */
export async function sendChatMessage(page, text) {
  const chat = gameChatLocator(page);
  await waitForGameChatReady(page);
  const input = chat.getByRole('textbox');
  await input.fill(text);
  const sendBtn = chat.getByRole('button', { name: /отпр|send/i });
  await expect(sendBtn).toBeEnabled({ timeout: 5000 });
  await sendBtn.click();
}

/** Дождаться текста в ленте чата. */
export async function expectChatMessage(page, text, { timeout = 15_000 } = {}) {
  const line = gameChatLocator(page).locator('.game-chat-text', { hasText: text });
  await expect(line).toBeVisible({ timeout });
}

/** Отправить сообщение в общий чат лобби (главная страница). */
export async function sendLobbyChatMessage(page, text) {
  const chat = page.locator('.lobby-chat');
  await expect(chat).toBeVisible({ timeout: 15_000 });
  const input = chat.getByRole('textbox');
  await input.fill(text);
  const sendBtn = chat.getByRole('button', { name: /lobbyChat\.send|отпр|send/i });
  await expect(sendBtn).toBeEnabled({ timeout: 10_000 });
  await sendBtn.click();
}

/** Дождаться текста в ленте лобби-чата. */
export async function expectLobbyChatMessage(page, text, { timeout = 15_000 } = {}) {
  const panel = page.locator('.lobby-chat .game-chat-text', { hasText: text });
  await expect(panel).toBeVisible({ timeout });
}
