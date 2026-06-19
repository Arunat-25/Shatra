import { describe, expect, it, vi } from 'vitest';
import { drawBoardFrame, drawBoardState } from './drawBoard';
import { computeBoardLayout } from './layoutMetrics';

function createMockCtx() {
  return {
    save: vi.fn(),
    restore: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    arcTo: vi.fn(),
    closePath: vi.fn(),
    fill: vi.fn(),
    stroke: vi.fn(),
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    strokeRect: vi.fn(),
    drawImage: vi.fn(),
    set fillStyle(_v) {},
    set strokeStyle(_v) {},
    set lineWidth(_v) {},
  };
}

describe('drawBoard', () => {
  it('draws board frame without throwing', () => {
    const layout = computeBoardLayout('белый', 320, 480);
    const ctx = createMockCtx();
    expect(() => drawBoardFrame(ctx, layout)).not.toThrow();
    expect(ctx.fill).toHaveBeenCalled();
  });

  it('draws board state without throwing', () => {
    const layout = computeBoardLayout('белый', 320, 480);
    const ctx = createMockCtx();
    const board = { 25: 'белый бий' };
    expect(() => drawBoardState(ctx, layout, {
      board,
      moveFrom: null,
      highlightedEssential: [],
      highlightedCaptured: [],
    })).not.toThrow();
    expect(ctx.fillRect).toHaveBeenCalled();
  });

  it('draws lite theme frame with lite palette', () => {
    const layout = computeBoardLayout('белый', 320, 480);
    const ctx = createMockCtx();
    let fillColor = '';
    Object.defineProperty(ctx, 'fillStyle', {
      set(v) { fillColor = v; },
      get() { return fillColor; },
    });
    drawBoardFrame(ctx, layout, 'lite');
    expect(fillColor).toBe('#ddd2c2');
  });
});
