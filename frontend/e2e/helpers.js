import { expect } from '@playwright/test';
import { computeBoardLayout, layoutDrawScale } from '../src/board/layoutMetrics.js';

/** Дождаться старта партии: зал ожидания скрыт, доска видна (DOM или canvas). */
export async function waitForGameBoard(page, { timeout = 60_000 } = {}) {
  await expect(page.locator('.waiting-screen')).toHaveCount(0, { timeout });
  const board = page.locator('.board-canvas, .room-board .kletka').first();
  await board.scrollIntoViewIfNeeded();
  await expect(board).toBeVisible({ timeout: 15_000 });
  return board;
}

/** Доска + интерактив (чат/WS) готовы к действиям. */
export async function waitForGameReady(page, opts) {
  await waitForGameBoard(page, opts);
  const chat = page.locator('.game-chat');
  if (await chat.count() === 0) return;

  const input = chat.getByRole('textbox');
  const sendBtn = chat.getByRole('button', { name: /отпр|send/i });
  await expect.poll(async () => {
    if (!(await input.isEnabled())) return false;
    await input.fill('…');
    const canSend = await sendBtn.isEnabled();
    await input.fill('');
    return canSend;
  }, { timeout: 30_000, message: 'Chat input never became ready' }).toBe(true);
}

export async function isCanvasBoard(page) {
  return (await page.locator('.board-canvas').count()) > 0;
}

async function readCanvasBoardMetrics(page, box) {
  return page.evaluate(() => {
    const board = document.querySelector('.room-board .board');
    if (!board) return null;
    const cs = getComputedStyle(board);
    const cellSize = parseFloat(cs.getPropertyValue('--cell-size'));
    const reserveSize = parseFloat(cs.getPropertyValue('--reserve-cell-size'));
    if (!Number.isFinite(cellSize) || cellSize <= 0) return null;
    return {
      cellSize,
      reserveSize: Number.isFinite(reserveSize) && reserveSize > 0 ? reserveSize : cellSize * 0.86,
    };
  }).then((metrics) => metrics || {
    cellSize: Math.min((box.height - 20) / 13.6, (box.width - 20) / 7),
    reserveSize: Math.min((box.height - 20) / 13.6, (box.width - 20) / 7) * 0.86,
  });
}

/** Центр клетки в координатах страницы (DOM или canvas). */
export async function getBoardCellCenter(page, cellId, myColor = 'белый') {
  const canvas = page.locator('.board-canvas');
  if (await canvas.count() > 0) {
    const box = await canvas.boundingBox();
    if (!box) throw new Error('Canvas board has no bounding box');
    const metrics = await readCanvasBoardMetrics(page, box);
    const layout = computeBoardLayout(myColor, metrics);
    const cell = layout.cells[cellId];
    if (!cell) throw new Error(`Cell ${cellId} not in layout`);
    const scale = layoutDrawScale(layout, box.width, box.height, true);
    return {
      x: box.x + scale.offsetX + (cell.x + cell.w / 2) * scale.x,
      y: box.y + scale.offsetY + (cell.y + cell.h / 2) * scale.y,
      isCanvas: true,
    };
  }
  const domCell = page.locator(`#position${cellId}`);
  await domCell.scrollIntoViewIfNeeded();
  const box = await domCell.boundingBox();
  if (!box) throw new Error(`Cell ${cellId} has no bounding box`);
  return {
    x: box.x + box.width / 2,
    y: box.y + box.height / 2,
    isCanvas: false,
  };
}

/** Клик по клетке на DOM- или canvas-доске. */
export async function clickBoardCell(page, cellId, myColor = 'белый') {
  const { x, y, isCanvas } = await getBoardCellCenter(page, cellId, myColor);
  if (isCanvas) {
    await page.mouse.click(x, y);
    return;
  }
  await page.locator(`#position${cellId}`).click();
}

/**
 * Перетащить фигуру с клетки и проверить визуальную обратную связь (ghost / canvas repaint).
 * @param {import('@playwright/test').Page} page
 * @param {number} cellId
 * @param {string} [myColor]
 * @param {{ delta?: number }} [opts]
 */
export async function expectPieceDragFeedback(page, cellId, myColor = 'белый', { delta = 48 } = {}) {
  const { x, y, isCanvas } = await getBoardCellCenter(page, cellId, myColor);

  await page.mouse.move(x, y);
  await page.mouse.down();

  if (isCanvas) {
    const before = await page.evaluate(() => document.querySelector('.board-canvas')?.toDataURL() ?? '');
    await page.mouse.move(x + delta, y + delta, { steps: 6 });
    const during = await page.evaluate(() => document.querySelector('.board-canvas')?.toDataURL() ?? '');
    await page.mouse.up();
    expect(during, 'canvas board should repaint while dragging').not.toBe(before);
    return;
  }

  await page.mouse.move(x + delta, y + delta, { steps: 6 });
  await expect(page.locator('.drag-ghost')).toBeVisible();
  await expect(page.locator('.board-content--dragging')).toBeVisible();
  await page.mouse.up();
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

export async function startPvpGame(hostPage, guestPage, { requireChat = true } = {}) {
  await hostPage.goto('/');
  await hostPage.getByRole('button', { name: /создать игру|create game|ойун түз/i }).click();
  await pickPlayAsWhite(hostPage);
  await hostPage.locator('.btn-setup-create').click();
  await expect(hostPage).toHaveURL(/\/[a-f0-9-]+(?:\?|$)/);
  const roomId = new URL(hostPage.url()).pathname.slice(1);
  await guestPage.goto(`/${roomId}`);
  if (requireChat) {
    await waitForGameReady(hostPage);
    await waitForGameReady(guestPage);
  } else {
    await waitForGameBoard(hostPage);
    await waitForGameBoard(guestPage);
  }
  return roomId;
}

/** Отправить сообщение в чат PvP (форма в боковой панели). */
export async function sendChatMessage(page, text) {
  await waitForGameReady(page);
  const chat = page.locator('.game-chat');
  await chat.scrollIntoViewIfNeeded();
  await expect(chat).toBeVisible();
  const input = chat.getByRole('textbox');
  await input.click();
  await input.fill(text);
  await expect(input).toHaveValue(text);
  const sendBtn = chat.getByRole('button', { name: /отпр|send/i });
  await expect(sendBtn).toBeEnabled({ timeout: 5000 });
  await sendBtn.click();
}

/** Дождаться текста в ленте чата. */
export async function expectChatMessage(page, text, { timeout = 15_000 } = {}) {
  const chat = page.locator('.game-chat');
  await chat.scrollIntoViewIfNeeded();
  await expect.poll(async () => {
    const texts = await page.locator('.game-chat-text').allTextContents();
    return texts.some((line) => line.includes(text));
  }, { timeout, message: `Expected chat to contain "${text}"` }).toBe(true);
}

/** Панель действий: sidebar на desktop, viewport-actions на mobile. */
export async function resolveGameActionsBar(page) {
  const sidebar = page.locator('.room-side-panel .game-actions-bar--sidebar');
  if (await sidebar.count()) {
    return sidebar;
  }
  return page.locator('.game-viewport-actions .game-actions-bar');
}

/** Завершить PvP сдачей (broadcast game_over обоим игрокам). */
export async function endPvpGameByResign(page) {
  const bar = await resolveGameActionsBar(page);
  const resignBtn = bar.locator('button.room-icon-btn--danger').first();
  await expect(resignBtn).toBeVisible();
  await resignBtn.click({ force: true });
  const armedBtn = bar.locator('button.room-icon-btn--resign-armed').first();
  await expect(armedBtn).toBeVisible({ timeout: 3000 });
  await armedBtn.click({ force: true });
}

function visibleGameOverBars(page) {
  return page.locator('.game-actions-bar--game-over').filter({ visible: true });
}

export function visibleOpponentDisconnectBanner(page) {
  return page.locator('.opponent-disconnect-status').filter({ visible: true });
}

export { visibleGameOverBars };

/** Завершить PvP до экрана результата (отмена до первого хода, optimistic на инициаторе). */
export async function endPvpGameForRematch(page) {
  const cancelBtn = page.getByRole('button', { name: /отменить игру|cancel/i });
  await expect(cancelBtn).toBeEnabled({ timeout: 10_000 });
  await cancelBtn.click();
  await expect(visibleGameOverBars(page).first()).toBeVisible({ timeout: 20_000 });
}

/** Двойной клик по «Сдаться» (arm + confirm). */
export async function resignGame(page) {
  await endPvpGameByResign(page);
}

/** После реванша — снова активная партия (не экран результата). */
export async function expectActiveGame(page, { timeout = 20_000 } = {}) {
  await expect(visibleGameOverBars(page)).toHaveCount(0, { timeout });
  await waitForGameBoard(page, { timeout });
}

/** Кнопка «Реванш» на экране результата. */
export async function clickRematch(page) {
  const btn = page.locator('.game-result-btn--rematch').filter({ visible: true }).first();
  await expect(btn).toBeEnabled({ timeout: 10_000 });
  await btn.click({ force: true });
}
