import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useTutorialCarousel, { TUTORIAL_INTERVAL_MS, TUTORIAL_SLIDE_COUNT } from './useTutorialCarousel';

describe('useTutorialCarousel', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('advances slide every 6 seconds', () => {
    const { result } = renderHook(() => useTutorialCarousel(TUTORIAL_SLIDE_COUNT));

    expect(result.current.index).toBe(0);

    act(() => {
      vi.advanceTimersByTime(TUTORIAL_INTERVAL_MS);
    });

    expect(result.current.index).toBe(1);

    act(() => {
      vi.advanceTimersByTime(TUTORIAL_INTERVAL_MS);
    });
    expect(result.current.index).toBe(2);

    act(() => {
      vi.advanceTimersByTime(TUTORIAL_INTERVAL_MS);
    });
    expect(result.current.index).toBe(3);

    act(() => {
      vi.advanceTimersByTime(TUTORIAL_INTERVAL_MS);
    });
    expect(result.current.index).toBe(0);
  });

  it('onClick advances immediately', () => {
    const { result } = renderHook(() => useTutorialCarousel(TUTORIAL_SLIDE_COUNT));

    act(() => {
      result.current.onClick();
    });

    expect(result.current.index).toBe(1);
  });

  it('pauses auto-advance while pointer is down', () => {
    const { result } = renderHook(() => useTutorialCarousel(TUTORIAL_SLIDE_COUNT));

    act(() => {
      result.current.onPointerDown();
    });

    act(() => {
      vi.advanceTimersByTime(TUTORIAL_INTERVAL_MS * 2);
    });

    expect(result.current.index).toBe(0);

    act(() => {
      result.current.onPointerUp();
    });

    act(() => {
      vi.advanceTimersByTime(TUTORIAL_INTERVAL_MS);
    });

    expect(result.current.index).toBe(1);
  });

  it('goTo jumps to a specific slide', () => {
    const { result } = renderHook(() => useTutorialCarousel(TUTORIAL_SLIDE_COUNT));

    act(() => {
      result.current.goTo(1);
    });

    expect(result.current.index).toBe(1);
  });
});
