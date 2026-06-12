import { test, expect } from '@playwright/test';
import { clickBoardCell, startAiGame } from './helpers.js';

const WHITE_OPENING = { from: 45, to: 37 };

test('mobile board stays visually full during AI thinking', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await startAiGame(page, { asWhite: true });

  await clickBoardCell(page, WHITE_OPENING.from, 'белый');
  await clickBoardCell(page, WHITE_OPENING.to, 'белый');

  await expect.poll(async () => page.evaluate(() => {
    const board = document.querySelector('.room-board .board');
    return board?.classList.contains('board-dimmed') ?? false;
  }), { timeout: 5000 }).toBe(true);

  const shot = await page.locator('.room-board .board').screenshot();
  const stats = await page.evaluate(() => {
    const heights = [...document.querySelectorAll('.room-board .kletka')]
      .map((c) => c.getBoundingClientRect().height);
    const board = document.querySelector('.room-board .board');
    const cs = board ? getComputedStyle(board) : null;
    return {
      minCellH: Math.min(...heights),
      boardOpacity: cs?.opacity,
      boardTransform: cs?.transform,
      boardUnit: cs?.getPropertyValue('--board-unit').trim(),
    };
  });

  expect(stats.minCellH).toBeGreaterThan(20);
  expect(stats.boardTransform === 'none' || stats.boardTransform?.includes('matrix(1')).toBeTruthy();
  expect(shot.length).toBeGreaterThan(8000);
});
