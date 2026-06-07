import { describe, expect, it, vi, beforeEach } from 'vitest';

const mockSentry = {
  addBreadcrumb: vi.fn(),
  captureMessage: vi.fn(),
  setTag: vi.fn(),
  setUser: vi.fn(),
};

vi.mock('./sentry', () => ({
  Sentry: mockSentry,
}));

describe('trackGameEvent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('adds breadcrumb for any event', async () => {
    const { trackGameEvent } = await import('./events');
    trackGameEvent('ws_connect', { roomId: 'abc' });
    expect(mockSentry.addBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'ws_connect', data: { roomId: 'abc' } }),
    );
    expect(mockSentry.captureMessage).not.toHaveBeenCalled();
  });

  it('captures message for key game events', async () => {
    const { trackGameEvent } = await import('./events');
    trackGameEvent('game_started', { roomId: 'abc' });
    expect(mockSentry.captureMessage).toHaveBeenCalledWith(
      'game_started',
      expect.objectContaining({ tags: { event: 'game_started' } }),
    );
  });
});

describe('trackWsEvent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('adds websocket breadcrumb without capture for connect', async () => {
    const { trackWsEvent } = await import('./events');
    trackWsEvent('ws_connect', { roomId: 'abc' });
    expect(mockSentry.addBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({ category: 'websocket', message: 'ws_connect' }),
    );
    expect(mockSentry.captureMessage).not.toHaveBeenCalled();
  });

  it('captures message for reconnect failure', async () => {
    const { trackWsEvent } = await import('./events');
    trackWsEvent('ws_reconnect_failed', { roomId: 'abc', attempts: 12 });
    expect(mockSentry.captureMessage).toHaveBeenCalledWith(
      'ws_reconnect_failed',
      expect.objectContaining({ tags: { event: 'ws_reconnect_failed' } }),
    );
  });
});

describe('trackApiError', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('records api breadcrumb', async () => {
    const { trackApiError } = await import('./events');
    trackApiError('/rooms', 500, 2);
    expect(mockSentry.addBreadcrumb).toHaveBeenCalledWith(
      expect.objectContaining({
        category: 'api',
        data: { resource: '/rooms', status: 500, attempt: 2 },
      }),
    );
  });
});

describe('setObservabilityUser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('sets client tag and user context', async () => {
    const { setObservabilityUser } = await import('./events');
    setObservabilityUser({ id: 'u1', username: 'alice' }, 'client-1');
    expect(mockSentry.setTag).toHaveBeenCalledWith('client_id', 'client-1');
    expect(mockSentry.setUser).toHaveBeenCalledWith({ id: 'u1', username: 'alice' });
  });

  it('clears user when logged out', async () => {
    const { setObservabilityUser } = await import('./events');
    setObservabilityUser(null, 'client-1');
    expect(mockSentry.setUser).toHaveBeenCalledWith(null);
  });
});
