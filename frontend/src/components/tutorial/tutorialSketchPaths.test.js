import { describe, expect, it } from 'vitest';
import {
  expandRect,
  mergeRelativeRects,
  placeLabelBesideBoard,
  sketchArrowPath,
  sketchRectPath,
} from './tutorialSketchPaths';

describe('tutorialSketchPaths', () => {
  it('merges relative rects', () => {
    const merged = mergeRelativeRects([
      { left: 0, top: 10, width: 50, height: 20 },
      { left: 0, top: 40, width: 50, height: 20 },
    ]);
    expect(merged).toEqual({ left: 0, top: 10, width: 50, height: 50 });
  });

  it('builds closed sketch path', () => {
    const d = sketchRectPath({ left: 10, top: 10, width: 40, height: 30 }, { seed: 1 });
    expect(d.startsWith('M ')).toBe(true);
    expect(d.endsWith(' Z')).toBe(true);
  });

  it('builds curved multi-segment arrow shaft and head', () => {
    const { shaft, head } = sketchArrowPath(0, 0, 100, 50, 2);
    expect(shaft.match(/Q/g)?.length).toBeGreaterThanOrEqual(2);
    expect(head).toContain('M 100');
  });

  it('uses a gentler curve on short arrows', () => {
    const short = sketchArrowPath(0, 0, 40, 10, 2).shaft;
    const long = sketchArrowPath(0, 0, 200, 80, 2).shaft;
    expect(short.match(/Q/g)?.length).toBe(1);
    expect(long.match(/Q/g)?.length).toBeGreaterThanOrEqual(2);
  });

  it('curveBoost adjusts short-arrow curvature', () => {
    const plain = sketchArrowPath(0, 0, 55, 20, 2).shaft;
    const boosted = sketchArrowPath(0, 0, 55, 20, 2, { curveBoost: 0.14 }).shaft;
    const straighter = sketchArrowPath(0, 0, 55, 20, 2, { curveBoost: -0.1 }).shaft;
    expect(boosted.match(/Q/g)?.length).toBeGreaterThanOrEqual(plain.match(/Q/g)?.length ?? 0);
    expect(straighter.match(/Q/g)?.length).toBeLessThanOrEqual(plain.match(/Q/g)?.length ?? 99);
  });

  it('expands rect for outline padding', () => {
    const outer = expandRect({ left: 10, top: 10, width: 40, height: 30 }, 14);
    expect(outer.left).toBe(-4);
    expect(outer.width).toBe(68);
  });

  it('places label beside board', () => {
    const pos = placeLabelBesideBoard(
      { left: 10, top: 20, width: 100, height: 200, right: 110, bottom: 220 },
      { width: 280, height: 300 },
      120,
      'Большое поле',
    );
    expect(pos.left).toBeGreaterThan(110);
    expect(pos.placement).toBe('beside');
  });
});
