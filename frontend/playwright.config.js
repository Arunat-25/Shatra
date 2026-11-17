import { defineConfig } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8000';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: process.env.CI ? 'github' : 'list',
  timeout: 60_000,
  use: {
    baseURL,
    trace: 'on-first-retry',
    headless: true,
    viewport: { width: 1400, height: 900 },
    // Локально на ubuntu 26.04 у Playwright нет сборки chromium —
    // запускается системный Chrome: PLAYWRIGHT_CHANNEL=chrome npx playwright test
    ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}),
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
