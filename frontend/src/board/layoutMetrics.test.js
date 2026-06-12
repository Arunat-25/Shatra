import { describe, expect, it } from 'vitest';
import { computeBoardLayout, hitTestCell } from './layoutMetrics';

describe('layoutMetrics', () => {
  it('maps known cell ids to rects inside board bounds', () => {
    const layout = computeBoardLayout('белый', 400, 600);
    expect(layout.cells[1]).toMatchObject({
      w: expect.any(Number),
      h: expect.any(Number),
    });
    expect(layout.cells[1].x).toBeGreaterThanOrEqual(0);
    expect(layout.cells[1].y).toBeGreaterThanOrEqual(0);
    expect(layout.cells[1].x + layout.cells[1].w).toBeLessThanOrEqual(layout.width);
  });

  it('hit-tests a point inside a cell', () => {
    const layout = computeBoardLayout('белый', 400, 600);
    const cell = layout.cells[25];
    const cx = cell.x + cell.w / 2;
    const cy = cell.y + cell.h / 2;
    expect(hitTestCell(layout.cells, cx, cy)).toBe(25);
    expect(hitTestCell(layout.cells, -1, -1)).toBeNull();
  });
});
