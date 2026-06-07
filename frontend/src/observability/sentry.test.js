import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const initMock = vi.fn();

vi.mock('@sentry/react', () => ({
  init: initMock,
  browserTracingIntegration: vi.fn(() => 'browserTracingIntegration'),
}));

describe('initSentry', () => {
  beforeEach(() => {
    vi.resetModules();
    initMock.mockClear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it('does not init without DSN', async () => {
    vi.stubEnv('VITE_SENTRY_DSN', '');
    const { initSentry } = await import('./sentry.js');
    initSentry();
    expect(initMock).not.toHaveBeenCalled();
  });

  it('initializes sentry with expected options when DSN is set', async () => {
    vi.stubEnv('VITE_SENTRY_DSN', 'https://example@sentry.io/1');
    vi.stubEnv('VITE_APP_VERSION', '1.0.0');
    const { initSentry } = await import('./sentry.js');
    initSentry();
    expect(initMock).toHaveBeenCalledWith(
      expect.objectContaining({
        dsn: 'https://example@sentry.io/1',
        release: '1.0.0',
        tracesSampleRate: 0.1,
        replaysSessionSampleRate: 0,
        replaysOnErrorSampleRate: 0,
      }),
    );
  });
});
