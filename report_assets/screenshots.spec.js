// Служебный скрипт для отчета: снимает реальные скриншоты работающего приложения
// Shatra (http://127.0.0.1:8000) для вставки в report_assets/img/.
// Запуск: cd frontend && npx playwright test ../report_assets/screenshots.spec.js --config=playwright.config.js
import { test, expect } from '@playwright/test';
import path from 'path';
import { fileURLToPath } from 'url';
import {
  waitForGameBoard,
  waitForGameReady,
  makeBoardMove,
  clickBoardCell,
  pickPlayAsWhite,
  endPvpGameByResign,
} from '../frontend/e2e/helpers.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, 'img');

function shot(name) {
  return path.join(OUT, `${name}.png`);
}

/**
 * Дождаться перехода со страницы лобби ("/") на страницу комнаты и вернуть roomId.
 * Не использует regex-проверку toHaveURL: baseURL — IP-адрес (127.0.0.1), и цифры
 * в адресе ложно совпадают с regex вида /\/[a-f0-9-]+/, поэтому ждём именно смену pathname.
 */
async function waitForRoomUrl(page, { timeout = 15_000 } = {}) {
  await expect.poll(() => new URL(page.url()).pathname, { timeout }).not.toBe('/');
  return new URL(page.url()).pathname.slice(1);
}

async function createPvpRoom(page, { asWhite = true, timerIndex = null } = {}) {
  await page.goto('/');
  await page.getByRole('button', { name: /создать игру|create game/i }).click();
  await expect(page.locator('.game-setup-picker')).toBeVisible();
  if (asWhite) await pickPlayAsWhite(page);
  if (timerIndex !== null) {
    await page.locator('.timer-presets .btn-timer-preset').nth(timerIndex).click().catch(() => {});
  }
  await page.locator('.btn-setup-create').click();
  return waitForRoomUrl(page);
}

test.describe.configure({ mode: 'serial' });

test('01 главная страница (лобби)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /шатра|shatra/i })).toBeVisible();
  await page.waitForTimeout(600);
  await page.screenshot({ path: shot('01-lobby'), fullPage: false });
});

test('02 создание игры — настройки партии', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  await page.getByRole('button', { name: /создать игру|create game/i }).click();
  await expect(page.locator('.game-setup-picker')).toBeVisible();
  await page.locator('.timer-presets .btn-timer-preset').filter({ hasText: /5/ }).first().click().catch(() => {});
  await page.waitForTimeout(300);
  await page.screenshot({ path: shot('02-create-room') });
});

test('03 список комнат в лобби', async ({ browser }) => {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const creator = await ctx.newPage();
  await createPvpRoom(creator, { asWhite: true });

  const viewer = await ctx.newPage();
  await viewer.goto('/');
  await viewer.waitForTimeout(1500);
  await expect(viewer.locator('.rooms-list')).toBeVisible();
  await viewer.screenshot({ path: shot('03-rooms-list') });
  await ctx.close();
});

test('04-07 партия PvP: старт, подсветка ходов, взятие, цепочка взятий', async ({ browser }) => {
  const hostCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const guestCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const host = await hostCtx.newPage(); // белые
  const guest = await guestCtx.newPage(); // черные

  const roomId = await createPvpRoom(host, { asWhite: true, timerIndex: 4 });
  await guest.goto(`/${roomId}`);
  await waitForGameReady(host);
  await waitForGameReady(guest);

  // 04 — доска в начале партии
  await host.waitForTimeout(500);
  await host.screenshot({ path: shot('04-board-initial') });

  // 05 — выбор фигуры, подсветка доступных ходов (45 -> подсветка перед ходом 45-37)
  await clickBoardCell(host, 45, 'белый');
  await host.waitForTimeout(500);
  await host.screenshot({ path: shot('05-move-hints') });
  await clickBoardCell(host, 37, 'белый');
  await host.waitForTimeout(700);

  // 06 — черные 23-29
  await makeBoardMove(guest, 23, 29, 'черный');

  // 07 — белые 44-45
  await makeBoardMove(host, 44, 45, 'белый');

  // 08 — черные 22-30 (создает обязательное взятие для белых с 37)
  await makeBoardMove(guest, 22, 30, 'черный');
  await host.waitForTimeout(500);

  // 09 — белые 37-23: взятие, цепочка обязана продолжиться
  await clickBoardCell(host, 37, 'белый');
  await host.waitForTimeout(400);
  await clickBoardCell(host, 23, 'белый');
  await host.waitForTimeout(700);
  await host.screenshot({ path: shot('06-capture-chain') });

  // 10 — белые 23-35: завершение цепочки взятий
  await clickBoardCell(host, 23, 'белый');
  await host.waitForTimeout(400);
  await clickBoardCell(host, 35, 'белый');
  await host.waitForTimeout(800);
  await host.screenshot({ path: shot('07-capture-result') });

  await hostCtx.close();
  await guestCtx.close();
});

test('08 партия с ботом', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  await page.getByRole('button', { name: /бот|bot|ai/i }).click();
  await pickPlayAsWhite(page);
  await page.locator('.btn-setup-create').click();
  await waitForRoomUrl(page);
  await waitForGameBoard(page);
  await makeBoardMove(page, 45, 37, 'белый');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: shot('08-ai-game') });
});

test('09 таймеры партии', async ({ browser }) => {
  const hostCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const guestCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const host = await hostCtx.newPage();
  const guest = await guestCtx.newPage();

  const roomId = await createPvpRoom(host, { asWhite: true, timerIndex: 3 });
  await guest.goto(`/${roomId}`);
  await waitForGameReady(host);
  await waitForGameReady(guest);
  await makeBoardMove(host, 45, 37, 'белый');
  await host.waitForTimeout(1500);
  await host.screenshot({ path: shot('09-timers') });

  await hostCtx.close();
  await guestCtx.close();
});

test('10 экран окончания партии', async ({ browser }) => {
  const hostCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const guestCtx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const host = await hostCtx.newPage();
  const guest = await guestCtx.newPage();

  const roomId = await createPvpRoom(host, { asWhite: true });
  await guest.goto(`/${roomId}`);
  await waitForGameReady(host);
  await waitForGameReady(guest);

  await endPvpGameByResign(host);
  await host.waitForTimeout(1200);
  await host.screenshot({ path: shot('10-game-over') });

  await hostCtx.close();
  await guestCtx.close();
});

test('11-12 переключение языка интерфейса (ru/en)', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/');
  await page.waitForTimeout(400);
  await page.screenshot({ path: shot('11-locale-ru') });
  await page.getByRole('button', { name: /english/i }).click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: shot('12-locale-en') });
});

test('13 мобильная версия', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: /бот|bot|ai/i }).click();
  await pickPlayAsWhite(page);
  await page.locator('.btn-setup-create').click();
  await waitForRoomUrl(page);
  await waitForGameBoard(page);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: shot('13-mobile') });
});
