import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { isDevProbeEnabled, sendDevProbe } from './devProbe';

describe('devProbe', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true })));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('isDevProbeEnabled is true in vitest dev mode', () => {
    expect(isDevProbeEnabled()).toBe(true);
  });

  it('sendDevProbe posts JSON in dev', () => {
    sendDevProbe({ sessionId: 'test', message: 'probe', data: { ok: true } });
    expect(fetch).toHaveBeenCalledTimes(1);
    const [url, init] = vi.mocked(fetch).mock.calls[0];
    expect(String(url)).toContain('/ingest/');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toMatchObject({ message: 'probe', data: { ok: true } });
  });
});
