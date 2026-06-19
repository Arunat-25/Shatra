import { describe, expect, it, vi } from 'vitest';
import { easeOutCubic, runSlideAnimation } from './slideAnimation';

describe('easeOutCubic', () => {
  it('starts at 0 and ends at 1', () => {
    expect(easeOutCubic(0)).toBe(0);
    expect(easeOutCubic(1)).toBe(1);
  });

  it('eases midpoints', () => {
    expect(easeOutCubic(0.5)).toBeGreaterThan(0.5);
  });
});

describe('runSlideAnimation', () => {
  it('finishes immediately when duration is 0', () => {
    const onFrame = vi.fn();
    const onComplete = vi.fn();
    runSlideAnimation({
      from: { x: 1, y: 2 },
      to: { x: 9, y: 8 },
      duration: 0,
      onFrame,
      onComplete,
    });
    expect(onFrame).toHaveBeenCalledWith(1, 9, 8);
    expect(onComplete).toHaveBeenCalledTimes(1);
  });

  it('runs frames until complete', () => {
    const frames = [];
    let now = 0;
    vi.spyOn(performance, 'now').mockImplementation(() => now);

    vi.stubGlobal('requestAnimationFrame', (cb) => {
      const step = () => {
        now += 40;
        cb(now);
        if (now < 200) requestAnimationFrame(cb);
      };
      step();
      return 1;
    });
    vi.stubGlobal('cancelAnimationFrame', vi.fn());

    const onComplete = vi.fn();
    runSlideAnimation({
      from: { x: 0, y: 0 },
      to: { x: 100, y: 0 },
      duration: 200,
      onFrame: (_t, x) => frames.push(x),
      onComplete,
    });

    expect(frames.length).toBeGreaterThan(0);
    expect(frames.at(-1)).toBe(100);
    expect(onComplete).toHaveBeenCalledTimes(1);

    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });
});
