import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useClockCountdown from './useClockCountdown';

describe('useClockCountdown', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('counts down active side between syncs', () => {
    const timer = { белый: 30, черный: 60 };
    const syncedAt = Date.now();
    const { result } = renderHook((props) => useClockCountdown(props), {
      initialProps: {
        timer,
        timerSyncedAt: syncedAt,
        moversColor: 'белый',
        timeControl: 300,
        gameOver: false,
        waiting: false,
      },
    });

    expect(result.current.белый).toBe(30);
    expect(result.current.черный).toBe(60);

    act(() => {
      vi.advanceTimersByTime(2000);
    });

    expect(result.current.белый).toBeCloseTo(28, 0);
    expect(result.current.черный).toBe(60);
  });

  it('returns raw timer when no time control', () => {
    const timer = { белый: 10, черный: 20 };
    const { result } = renderHook(() => useClockCountdown({
      timer,
      timerSyncedAt: Date.now(),
      moversColor: 'белый',
      timeControl: null,
      gameOver: false,
      waiting: false,
    }));

    expect(result.current).toEqual(timer);
  });
});
