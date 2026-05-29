import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
} from '../constants/profile';
import {
  clearScheduledTokenRefresh,
  clearTokens,
  computeRefreshDelayMs,
  decodeAccessExp,
  scheduleTokenRefresh,
  setTokens,
} from './auth';

function makeToken(payload) {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe('decodeAccessExp', () => {
  it('returns exp from valid payload', () => {
    const exp = Math.floor(Date.now() / 1000) + 3600;
    expect(decodeAccessExp(makeToken({ sub: '1', exp }))).toBe(exp);
  });

  it('returns null for invalid token', () => {
    expect(decodeAccessExp('not-a-jwt')).toBeNull();
  });

  it('returns null when exp missing', () => {
    expect(decodeAccessExp(makeToken({ sub: '1' }))).toBeNull();
  });
});

describe('computeRefreshDelayMs', () => {
  const NOW = 1_700_000_000_000;

  it('schedules 2 minutes before exp', () => {
    const exp = Math.floor(NOW / 1000) + 600;
    const delay = computeRefreshDelayMs(exp, NOW);
    expect(delay).toBe(600_000 - 120_000);
  });

  it('never below 5 seconds', () => {
    const exp = Math.floor(NOW / 1000) + 30;
    expect(computeRefreshDelayMs(exp, NOW)).toBe(5000);
  });

  it('uses 5s minimum when exp already passed', () => {
    const exp = Math.floor(NOW / 1000) - 60;
    expect(computeRefreshDelayMs(exp, NOW)).toBe(5000);
  });
});

function mockLocalStorage() {
  const storage = {};
  global.localStorage = {
    getItem: (k) => (k in storage ? storage[k] : null),
    setItem: (k, v) => { storage[k] = String(v); },
    removeItem: (k) => { delete storage[k]; },
    clear: () => { Object.keys(storage).forEach((k) => delete storage[k]); },
  };
  return storage;
}

describe('scheduleTokenRefresh', () => {
  beforeEach(() => {
    mockLocalStorage();
    vi.useFakeTimers();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    clearScheduledTokenRefresh();
    clearTokens();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('does nothing without access token', () => {
    scheduleTokenRefresh();
    vi.advanceTimersByTime(60_000);
    expect(fetch).not.toHaveBeenCalled();
  });

  it('calls refresh endpoint before exp', async () => {
    const exp = Math.floor(Date.now() / 1000) + 400;
    localStorage.setItem(ACCESS_TOKEN_KEY, makeToken({ exp }));
    localStorage.setItem(REFRESH_TOKEN_KEY, 'refresh-plain');

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        access_token: makeToken({ exp: exp + 3600 }),
        refresh_token: 'new-refresh',
      }),
    });

    scheduleTokenRefresh();
    await vi.advanceTimersByTimeAsync(computeRefreshDelayMs(exp));

    expect(fetch).toHaveBeenCalledWith(
      '/api/auth/refresh',
      expect.objectContaining({ method: 'POST' }),
    );
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBe('new-refresh');
  });

  it('clears tokens when refresh fails', async () => {
    const exp = Math.floor(Date.now() / 1000) + 400;
    localStorage.setItem(ACCESS_TOKEN_KEY, makeToken({ exp }));
    localStorage.setItem(REFRESH_TOKEN_KEY, 'bad-refresh');
    fetch.mockResolvedValueOnce({ ok: false, status: 401 });

    scheduleTokenRefresh();
    await vi.advanceTimersByTimeAsync(computeRefreshDelayMs(exp));

    expect(localStorage.getItem(ACCESS_TOKEN_KEY)).toBeNull();
    expect(localStorage.getItem(REFRESH_TOKEN_KEY)).toBeNull();
  });

  it('setTokens schedules refresh', () => {
    const exp = Math.floor(Date.now() / 1000) + 800;
    setTokens(makeToken({ exp }), 'r1');
    expect(vi.getTimerCount()).toBeGreaterThan(0);
  });

  it('clearTokens cancels scheduled refresh', async () => {
    const exp = Math.floor(Date.now() / 1000) + 400;
    setTokens(makeToken({ exp }), 'r1');
    clearTokens();
    await vi.advanceTimersByTimeAsync(600_000);
    expect(fetch).not.toHaveBeenCalled();
  });
});
