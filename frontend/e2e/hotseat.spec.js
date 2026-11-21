import { test, expect } from '@playwright/test';
import { waitForGameBoard, clickBoardCell } from './helpers';

const firstCellLabel = (page) =>
  page.locator('.room-board .kletka').first().innerText();

test.describe('hotseat — партия на одном устройстве', () => {
  test('стартует мгновенно, применяет ходы обоих игроков и переворачивает доску', async ({ page }) => {
    await page.goto('/local?mode=hotseat');
    await waitForGameBoard(page);

    // Белый вид: первая клетка доски — клетка 1.
    await expect.poll(() => firstCellLabel(page), { timeout: 15_000 }).toBe('1');

    // Фигуры на доске = локальная сессия выставила состояние (GAME_STARTED).
    await expect(
      page.locator('.room-board .kletka svg').first(),
    ).toBeVisible({ timeout: 15_000 });

    // Ход белых: шатра 40 -> 32. Пауза между кликами — как у живого игрока:
    // второй клик должен прийти после коммита селекции.
    await clickBoardCell(page, 40, 'белый');
    await page.waitForTimeout(300);
    await clickBoardCell(page, 32, 'белый');

    // Доска развернулась к чёрным: первая клетка теперь 62.
    await expect.poll(() => firstCellLabel(page), { timeout: 15_000 }).toBe('62');

    // Ход чёрных: шатра 20 -> 26 — ход принимается (доска снова к белым).
    await clickBoardCell(page, 20, 'черный');
    await page.waitForTimeout(300);
    await clickBoardCell(page, 26, 'черный');
    await expect.poll(() => firstCellLabel(page), { timeout: 15_000 }).toBe('1');

    // Чат в хотсите отсутствует (сервер не нужен).
    await expect(page.locator('.game-chat')).toHaveCount(0);
  });

  test('не требует сервера: страница открывается без сетевых сущностей', async ({ page }) => {
    const response = await page.goto('/local?mode=hotseat');
    expect(response.ok()).toBeTruthy();
    await waitForGameBoard(page, { timeout: 20_000 });
    await expect(page.locator('.waiting-screen')).toHaveCount(0);
  });

  test('офлайн: хотсит доступен после первой загрузки (PWA)', async ({ browser }) => {
    // По умолчанию Playwright блокирует service workers — включаем явно.
    const context = await browser.newContext({ serviceWorkers: 'allow' });
    const page = await context.newPage();
    try {
      await page.goto('/local?mode=hotseat');
      await expect(page.locator('.room-board .kletka svg').first()).toBeVisible({ timeout: 15_000 });
      // Дать service worker завершить прекэш.
      await page.evaluate(async () => {
        const reg = await navigator.serviceWorker.ready;
        await reg.active; // активный воркер
      });
      await page.waitForTimeout(1000);

      await context.setOffline(true);
      await page.reload();
      await expect.poll(() => firstCellLabel(page), { timeout: 20_000 }).toBe('1');
      await expect(page.locator('.room-board .kletka svg').first()).toBeVisible({ timeout: 15_000 });
      await expect(page.locator('.waiting-screen')).toHaveCount(0);
    } finally {
      await context.close();
    }
  });
});
