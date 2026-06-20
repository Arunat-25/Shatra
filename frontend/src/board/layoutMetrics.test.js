import { describe, expect, it } from 'vitest';
import {
  BOARD_HEIGHT_UNITS,
  BOARD_HEIGHT_UNITS_COMPACT,
  BOARD_WIDTH_CELLS,
  computeBoardLayout,
  hitTestCell,
  layoutDrawScale,
  viewportToLayoutPoint,
} from './layoutMetrics';

const DESKTOP_METRICS = {
  cellSize: 40,
  reserveSize: 34.4,
  reserveMargin: 3,
  mainMargin: 1,
  kingMargin: 3.78,
  heightUnits: BOARD_HEIGHT_UNITS,
};

const MOBILE_METRICS = {
  cellSize: 40,
  reserveSize: 34.4,
  reserveMargin: 0,
  mainMargin: 0,
  kingMargin: 0,
  heightUnits: BOARD_HEIGHT_UNITS_COMPACT,
};

describe('layoutMetrics', () => {
  it('maps known cell ids to rects inside board bounds', () => {
    const layout = computeBoardLayout('белый', DESKTOP_METRICS);
    expect(layout.cells[1]).toMatchObject({
      w: expect.any(Number),
      h: expect.any(Number),
    });
    expect(layout.cells[1].x).toBeGreaterThanOrEqual(0);
    expect(layout.cells[1].y).toBeGreaterThanOrEqual(0);
    expect(layout.cells[1].x + layout.cells[1].w).toBeLessThanOrEqual(layout.width);
    expect(layout.width).toBe(BOARD_WIDTH_CELLS * DESKTOP_METRICS.cellSize);
    expect(layout.height).toBeGreaterThanOrEqual(BOARD_HEIGHT_UNITS * DESKTOP_METRICS.cellSize * 0.9);
  });

  it('mobile compact layout is shorter than desktop with margins', () => {
    const desktop = computeBoardLayout('белый', DESKTOP_METRICS);
    const mobile = computeBoardLayout('белый', MOBILE_METRICS);
    expect(mobile.contentHeight).toBeLessThan(desktop.contentHeight);
    expect(mobile.height).toBeLessThan(desktop.height);
    expect(MOBILE_METRICS.heightUnits).toBe(BOARD_HEIGHT_UNITS_COMPACT);
    expect(DESKTOP_METRICS.heightUnits).toBe(BOARD_HEIGHT_UNITS);
    expect(BOARD_HEIGHT_UNITS_COMPACT * MOBILE_METRICS.cellSize).toBeLessThan(
      BOARD_HEIGHT_UNITS * DESKTOP_METRICS.cellSize,
    );
  });

  it('hit-tests a point inside a cell', () => {
    const layout = computeBoardLayout('белый', DESKTOP_METRICS);
    const cell = layout.cells[25];
    const cx = cell.x + cell.w / 2;
    const cy = cell.y + cell.h / 2;
    expect(hitTestCell(layout.cells, cx, cy)).toBe(25);
    expect(hitTestCell(layout.cells, -1, -1)).toBeNull();
  });

  it('layoutDrawScale uses uniform scale when filling slot', () => {
    const layout = computeBoardLayout('белый', MOBILE_METRICS);
    const scale = layoutDrawScale(layout, 360, 520, true);
    expect(scale.x).toBeCloseTo(scale.y, 10);
    const cell = layout.cells[25];
    expect(cell.w * scale.x).toBeCloseTo(cell.h * scale.y, 5);
  });

  it('layoutDrawScale is identity when not filling slot', () => {
    const layout = computeBoardLayout('белый', DESKTOP_METRICS);
    expect(layoutDrawScale(layout, 400, 600, false)).toEqual({
      x: 1,
      y: 1,
      offsetX: 0,
      offsetY: 0,
    });
  });

  it('viewportToLayoutPoint inverts canvas draw transform', () => {
    const layout = computeBoardLayout('белый', MOBILE_METRICS);
    const displayW = 360;
    const displayH = 520;
    const scale = layoutDrawScale(layout, displayW, displayH, true);
    const cell = layout.cells[25];
    const layoutCx = cell.x + cell.w / 2;
    const layoutCy = cell.y + cell.h / 2;
    const canvasRect = { left: 10, top: 20, width: displayW, height: displayH };
    const clientX = canvasRect.left + scale.offsetX + layoutCx * scale.x;
    const clientY = canvasRect.top + scale.offsetY + layoutCy * scale.y;
    const point = viewportToLayoutPoint(clientX, clientY, canvasRect, layout, true);
    expect(point.x).toBeCloseTo(layoutCx, 5);
    expect(point.y).toBeCloseTo(layoutCy, 5);
  });

  it('hit-tests in CSS pixels (not device pixels)', () => {
    const layout = computeBoardLayout('белый', { ...DESKTOP_METRICS, cellSize: 36, reserveSize: 30.96 });
    const cell = layout.cells[10];
    const cssX = cell.x + cell.w * 0.5;
    const cssY = cell.y + cell.h * 0.5;
    expect(hitTestCell(layout.cells, layout.width + 100, layout.height + 100)).toBeNull();
    expect(hitTestCell(layout.cells, cssX, cssY)).toBe(10);
  });
});
