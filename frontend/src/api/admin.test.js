import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  fetchGamesSeries,
  fetchGamesStats,
  fetchOnlinePeriodStats,
  fetchOnlineSeries,
  fetchOnlineStats,
  fetchRegistrationSeries,
  fetchRegistrationStats,
} from './admin';

vi.mock('./auth', () => ({
  authFetch: vi.fn(),
}));

import { authFetch } from './auth';

describe('admin api client', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('fetchRegistrationStats builds period query', async () => {
    authFetch.mockResolvedValue({ total: 3 });
    await fetchRegistrationStats({ period: '7d' });
    expect(authFetch).toHaveBeenCalledWith('/api/admin/stats/registrations?period=7d');
  });

  it('fetchRegistrationStats builds from/to query for custom range', async () => {
    authFetch.mockResolvedValue({ total: 1 });
    await fetchRegistrationStats({
      from: '2026-05-29T00:00:00.000Z',
      to: '2026-05-29T12:00:00.000Z',
    });
    expect(authFetch).toHaveBeenCalledWith(
      '/api/admin/stats/registrations?from=2026-05-29T00%3A00%3A00.000Z&to=2026-05-29T12%3A00%3A00.000Z',
    );
  });

  it('fetchOnlinePeriodStats builds period query', async () => {
    authFetch.mockResolvedValue({ total_unique: 2 });
    await fetchOnlinePeriodStats({ period: '7d' });
    expect(authFetch).toHaveBeenCalledWith('/api/admin/stats/online/period?period=7d');
  });

  it('fetchOnlineStats sends at parameter', async () => {
    authFetch.mockResolvedValue({ total_unique: 1 });
    await fetchOnlineStats('2026-05-29T10:00:00.000Z');
    expect(authFetch).toHaveBeenCalledWith(
      '/api/admin/stats/online?at=2026-05-29T10%3A00%3A00.000Z',
    );
  });

  it('fetchGamesStats includes filters', async () => {
    authFetch.mockResolvedValue({ total: 0 });
    await fetchGamesStats({
      period: '30d',
      room_type: 'public',
      anonymous_players: '1',
    });
    expect(authFetch).toHaveBeenCalledWith(
      '/api/admin/stats/games?period=30d&room_type=public&anonymous_players=1',
    );
  });

  it('fetchRegistrationSeries uses series endpoint', async () => {
    authFetch.mockResolvedValue({ buckets: [], granularity: 'day' });
    await fetchRegistrationSeries({ period: '7d' });
    expect(authFetch).toHaveBeenCalledWith('/api/admin/stats/registrations/series?period=7d');
  });

  it('fetchOnlineSeries uses series endpoint', async () => {
    authFetch.mockResolvedValue({ buckets: [], granularity: 'day' });
    await fetchOnlineSeries({ period: '24h' });
    expect(authFetch).toHaveBeenCalledWith('/api/admin/stats/online/series?period=24h');
  });

  it('fetchGamesSeries includes filters', async () => {
    authFetch.mockResolvedValue({ buckets: [], granularity: 'day' });
    await fetchGamesSeries({ period: '7d', room_type: 'ai' });
    expect(authFetch).toHaveBeenCalledWith(
      '/api/admin/stats/games/series?period=7d&room_type=ai',
    );
  });

  it('fetchRegistrationSeries builds custom from/to query', async () => {
    authFetch.mockResolvedValue({ buckets: [], granularity: 'day' });
    await fetchRegistrationSeries({
      from: '2026-05-01T00:00:00.000Z',
      to: '2026-05-04T00:00:00.000Z',
    });
    expect(authFetch).toHaveBeenCalledWith(
      '/api/admin/stats/registrations/series?from=2026-05-01T00%3A00%3A00.000Z&to=2026-05-04T00%3A00%3A00.000Z',
    );
  });

  it('fetchGamesSeries includes anonymous_players filter', async () => {
    authFetch.mockResolvedValue({ buckets: [], granularity: 'hour' });
    await fetchGamesSeries({ period: '24h', anonymous_players: '1' });
    expect(authFetch).toHaveBeenCalledWith(
      '/api/admin/stats/games/series?period=24h&anonymous_players=1',
    );
  });
});
