import { test, expect } from '@playwright/test';
import { waitForGameBoard } from './helpers.js';

test('lobby → AI game → board cell click', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /шатра|shatra/i })).toBeVisible();

  await page.getByRole('button', { name: /бот|bot|ai/i }).click();
  await page.locator('.btn-setup-create').click();

  await expect(page).toHaveURL(/\/[a-f0-9-]+(\?mode=ai)?/);

  const cell = await waitForGameBoard(page);
  await cell.click();
  await expect(cell).toBeVisible();
});
