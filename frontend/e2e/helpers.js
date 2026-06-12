import { expect } from '@playwright/test';
import { computeBoardLayout } from '../src/board/layoutMetrics.js';

/** Дождаться старта партии: зал ожидания скрыт, доска видна (DOM или canvas). */
export async function waitForGameBoard(page, { timeout = 60_000 } = {}) {
  await expect(page.locator('.waiting-screen')).toHaveCount(0, { timeout });
  const board = page.locator('.board-canvas, .room-board .kletka').first();
  await board.scrollIntoViewIfNeeded();
  await expect(board).toBeVisible({ timeout: 15_000 });
  return board;
}

export async function isCanvasBoard(page) {
  return (await page.locator('.board-canvas').count()) > 0;
}

/** Клик по клетке на DOM- или canvas-доске. */
export async function clickBoardCell(page, cellId, myColor = 'белый') {
  const canvas = page.locator('.board-canvas');
  if (await canvas.count() > 0) {
    const box = await canvas.boundingBox();
    if (!box) throw new Error('Canvas board has no bounding box');
    const layout = computeBoardLayout(myColor, box.width, box.height);
    const cell = layout.cells[cellId];
    if (!cell) throw new Error(`Cell ${cellId} not in layout`);
    const x = box.x + cell.x + cell.w / 2;
    const y = box.y + cell.y + cell.h / 2;
    await page.mouse.click(x, y);
    return;
  }
  const domCell = page.locator(`#position${cellId}`);
  await domCell.scrollIntoViewIfNeeded();
  await domCell.click();
}

/** Выбрать фигуру и сходить (from → to). */
export async function makeBoardMove(page, fromId, toId, myColor = 'белый') {
  await clickBoardCell(page, fromId, myColor);
  await page.waitForTimeout((await isCanvasBoard(page)) ? 500 : 1200);
  await clickBoardCell(page, toId, myColor);
  await page.waitForTimeout(800);
}

export async function expectMoveHistoryContains(page, text, { timeout = 20_000 } = {}) {
  await expect.poll(async () => {
    const lines = await page.locator('.move-history-line').allTextContents();
    return lines.some((line) => line.includes(text));
  }, { timeout, message: `Expected move history to contain "${text}"` }).toBe(true);
}

export async function pickPlayAsWhite(page) {
  const whiteBtn = page.locator('.game-setup-picker .btn-color-pick').filter({ hasText: /белые|white/i });
  await expect(whiteBtn).toBeVisible();
  await whiteBtn.click();
}

export async function startAiGame(page, { asWhite = true } = {}) {
  await page.goto('/');
  await page.getByRole('button', { name: /бот|bot|ai/i }).click();
  if (asWhite) {
    await pickPlayAsWhite(page);
  }
  await page.locator('.btn-setup-create').click();
  await expect(page).toHaveURL(/\/[a-f0-9-]+(\?mode=ai)?/);
  await waitForGameBoard(page);
}

export async function startPvpGame(hostPage, guestPage) {
  await hostPage.goto('/');
  await hostPage.getByRole('button', { name: /создать игру|create game|ойун түз/i }).click();
  await pickPlayAsWhite(hostPage);
  await hostPage.locator('.btn-setup-create').click();
  await expect(hostPage).toHaveURL(/\/[a-f0-9]{8}(?:\?|$)/);
  const roomId = new URL(hostPage.url()).pathname.slice(1);
  await guestPage.goto(`/${roomId}`);
  await waitForGameBoard(hostPage);
  await waitForGameBoard(guestPage);
  return roomId;
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
