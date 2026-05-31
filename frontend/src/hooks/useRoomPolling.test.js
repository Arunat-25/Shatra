import { describe, expect, it, vi } from 'vitest';
import useRoomPolling from './useRoomPolling';
import { renderHook, waitFor } from '@testing-library/react';

describe('useRoomPolling stats', () => {
  it('stores stats from fetch response', async () => {
    const fetchFn = vi.fn().mockResolvedValue({
      rooms: [{ room_id: 'abc' }],
      stats: { online_total: 3, active_games: 1, waiting_public_rooms: 1 },
    });
    const { result } = renderHook(() => useRoomPolling(fetchFn, 60_000));
    await waitFor(() => {
      expect(result.current.stats?.online_total).toBe(3);
    });
    expect(result.current.stats.active_games).toBe(1);
  });
});
