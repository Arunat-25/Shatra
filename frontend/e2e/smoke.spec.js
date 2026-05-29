import { test, expect } from '@playwright/test';

test('lobby → AI game → board cell click', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /шатра/i })).toBeVisible();

  await page.getByRole('button', { name: /бот|bot|ai/i }).click();
  await page.locator('.btn-setup-create').click();

  await expect(page).toHaveURL(/\/[a-f0-9-]+(\?mode=ai)?/);

  const cell = page.locator('.room-board .kletka').first();
  await expect(cell).toBeVisible({ timeout: 30_000 });

  await cell.click();
  await expect(cell).toBeVisible();
});
