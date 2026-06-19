import { describe, expect, it, vi } from 'vitest';
import { drawBoardFrame, drawBoardState, drawCellNumbers } from './drawBoard';
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
    fillText: vi.fn(),
    set fillStyle(_v) {},
    set strokeStyle(_v) {},
    set lineWidth(_v) {},
  };
}

const TEST_LAYOUT_METRICS = { cellSize: 40, reserveSize: 34.4 };

describe('drawBoard', () => {
  it('draws board frame without throwing', () => {
    const layout = computeBoardLayout('белый', TEST_LAYOUT_METRICS);
    const ctx = createMockCtx();
    expect(() => drawBoardFrame(ctx, layout)).not.toThrow();
    expect(ctx.fill).toHaveBeenCalled();
  });

  it('draws board state without throwing', () => {
    const layout = computeBoardLayout('белый', TEST_LAYOUT_METRICS);
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

  it('draws lite board frame as full opaque pad', () => {
    const layout = computeBoardLayout('белый', TEST_LAYOUT_METRICS);
    const ctx = createMockCtx();
    drawBoardFrame(ctx, layout, 'lite', 'белый');
    expect(ctx.fill).not.toHaveBeenCalled();
    expect(ctx.fillRect).toHaveBeenCalledWith(0, 0, layout.width, layout.contentHeight);
  });

  it('draws compact cell numbers with smaller scale', () => {
    const layout = computeBoardLayout('белый', TEST_LAYOUT_METRICS);
    const ctx = createMockCtx();
    ctx.font = '';
    Object.defineProperty(ctx, 'font', {
      set(v) { ctx._font = v; },
      get() { return ctx._font; },
    });
    drawCellNumbers(ctx, layout, { scale: 0.12 });
    expect(ctx.fillText).toHaveBeenCalled();
    expect(ctx._font).toMatch(/700 5px/);
  });

  it('draws board state with cell numbers when enabled', () => {
    const layout = computeBoardLayout('белый', TEST_LAYOUT_METRICS);
    const ctx = createMockCtx();
    drawBoardState(ctx, layout, {
      board: {},
      moveFrom: null,
      highlightedEssential: [],
      highlightedCaptured: [],
      showCellNumbers: true,
    });
    expect(ctx.fillText).toHaveBeenCalled();
  });
});
