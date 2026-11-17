import { test, expect } from '@playwright/test';
import { waitForGameBoard, getBoardCellCenter } from './helpers';

test.describe('hotseat — партия на одном устройстве', () => {
  test('стартует мгновенно, применяет ход и переворачивает доску к текущему игроку', async ({ page }) => {
    await page.goto('/local?mode=hotseat');
    await waitForGameBoard(page);

    const selfBar = page.locator('.game-player-bar--self');
    await expect(selfBar).toHaveCount(1);
    const beforeText = await selfBar.innerText();

    // Ход белых: шатра 40 -> 32 (легальный первый ход).
    const from = await getBoardCellCenter(page, 40, 'белый');
    await page.mouse.click(from.x, from.y);
    const to = await getBoardCellCenter(page, 32, 'белый');
    await page.mouse.click(to.x, to.y);

    // После хода доска развёрнута к чёрным — своя плашка сменилась.
    await expect
      .poll(async () => selfBar.innerText(), { timeout: 15_000 })
      .not.toBe(beforeText);

    // Чат в хотсите отсутствует (сервер не нужен).
    await expect(page.locator('.game-chat')).toHaveCount(0);
  });

  test('не требует сервера: страница не ждёт сетевых сущностей', async ({ page }) => {
    // Прямой заход по URL без создания комнаты через API.
    const response = await page.goto('/local?mode=hotseat');
    expect(response.ok()).toBeTruthy();
    await waitForGameBoard(page, { timeout: 20_000 });
    await expect(page.locator('.waiting-screen')).toHaveCount(0);
  });
});
