import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { getAccessTokenMock } = vi.hoisted(() => ({
  getAccessTokenMock: vi.fn(),
}));

const trackApiErrorMock = vi.hoisted(() => vi.fn());

vi.mock('./api/auth', () => ({
  getAccessToken: getAccessTokenMock,
}));

vi.mock('./observability/events', () => ({
  trackApiError: (...args) => trackApiErrorMock(...args),
}));

vi.mock('./i18n', () => ({
  default: { t: (key) => key },
}));

import { getWsUrl, listRooms, createRoom } from './api';

describe('getWsUrl', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => 'client-abc'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    getAccessTokenMock.mockReset();
  });

  it('includes client_id only when not logged in', () => {
    getAccessTokenMock.mockReturnValue(null);
    vi.stubGlobal('window', {
      location: { protocol: 'http:', host: 'localhost:5173' },
    });

    const url = getWsUrl('room123');
    expect(url).toBe('ws://localhost:5173/ws/v2/room123/?client_id=client-abc');
    expect(url).not.toContain('access_token');
  });

  it('defaults to v2 websocket path', () => {
    getAccessTokenMock.mockReturnValue(null);
    vi.stubGlobal('window', {
      location: { protocol: 'http:', host: 'localhost:5173' },
    });

    const url = getWsUrl('room123');
    expect(url).toBe('ws://localhost:5173/ws/v2/room123/?client_id=client-abc');
  });

  it('includes access_token when logged in', () => {
    getAccessTokenMock.mockReturnValue('jwt-token-xyz');
    vi.stubGlobal('window', {
      location: { protocol: 'https:', host: 'shatra.example' },
    });

    const url = getWsUrl('room456');
    expect(url).toBe(
      'wss://shatra.example/ws/v2/room456/?client_id=client-abc&access_token=jwt-token-xyz',
    );
  });
});

describe('listRooms', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => 'client-abc'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    });
    getAccessTokenMock.mockReturnValue(null);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ rooms: [] }),
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    getAccessTokenMock.mockReset();
  });

  it('includes client_id in query string', async () => {
    await listRooms();
    expect(fetch).toHaveBeenCalledWith(
      '/rooms?client_id=client-abc',
      expect.objectContaining({ headers: expect.any(Object) }),
    );
  });

  it('tracks api error after retries exhausted', async () => {
    trackApiErrorMock.mockClear();
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')));
    await expect(listRooms()).rejects.toThrow();
    expect(trackApiErrorMock).toHaveBeenCalledWith(
      '/rooms?client_id=client-abc',
      'network',
      2,
    );
  });
});

describe('createRoom', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => 'client-abc'),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    });
    getAccessTokenMock.mockReturnValue(null);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ room_id: 'room1', type: 'private' }),
    }));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    getAccessTokenMock.mockReset();
  });

  it('includes rated flag for private rated rooms', async () => {
    await createRoom('private', null, 0, 'random', true);
    const [, options] = fetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.rated).toBe(true);
    expect(body.type).toBe('private');
  });

  it('omits rated flag for public rooms', async () => {
    await createRoom('public', null, 0, 'random', true);
    const [, options] = fetch.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.rated).toBeUndefined();
    expect(body.type).toBe('public');
  });
});
