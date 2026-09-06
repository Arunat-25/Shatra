// Отдельный конфиг Playwright для служебных скриптов отчета (report_assets/).
// Не изменяет frontend/playwright.config.js, использует то же приложение.
// (без импорта defineConfig — во избежание проблем разрешения модулей за пределами frontend/)

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8000';

export default ({
  testDir: '.',
  testMatch: /screenshots\.spec\.js/,
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: 'list',
  timeout: 90_000,
  use: {
    baseURL,
    trace: 'off',
    headless: true,
    viewport: { width: 1440, height: 900 },
  },
  projects: [{ name: 'chromium', use: { browserName: 'chromium' } }],
});
