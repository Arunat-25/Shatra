import { describe, expect, it } from 'vitest';
import {
  TOLERANCE_PX,
  assertBoardLayout,
  compareBoardSnapshots,
  readBoardLayoutSnapshot,
  rectsMatch,
  withinTolerance,
} from './boardLayoutGeometry';

function makeSnapshot(overrides = {}) {
  return {
    viewport: { width: 1400, height: 900 },
    mode: { isLite: false, isCanvas: false, isCompact: false },
    slot: { x: 0, y: 100, width: 560, height: 700 },
    board: { x: 0, y: 100, width: 560, height: 680 },
    content: { x: 14, y: 114, width: 532, height: 652 },
    canvas: null,
    topBar: { x: 0, y: 60, width: 560, height: 40 },
    bottomBar: { x: 0, y: 780, width: 560, height: 40 },
    gapBelowTopBar: 0,
    gapAboveBottomBar: 0,
    contentInsetTop: 14,
    contentInsetBottom: 14,
    boardOverflowsSlot: false,
    contentOverflowsBoard: false,
    overlapsTopBar: false,
    fortTopVisible: true,
    fortBottomVisible: true,
    boardUnit: 'min(calc((100cqh - 20px) / 13.6), calc((100cqw - 20px) / 7))',
    heightUnits: '13.6',
    paddingTop: 14,
    paddingBottom: 14,
    boardFlexShrink: '1',
    ...overrides,
  };
}

describe('boardLayoutGeometry', () => {
  it('withinTolerance allows small drift', () => {
    expect(withinTolerance(14, 15, TOLERANCE_PX)).toBe(true);
    expect(withinTolerance(14, 20, TOLERANCE_PX)).toBe(false);
  });

  it('rectsMatch compares geometry within tolerance', () => {
    const a = { x: 10, y: 20, width: 300, height: 400 };
    const b = { x: 11, y: 21, width: 301, height: 401 };
    expect(rectsMatch(a, b)).toBe(true);
    expect(rectsMatch(a, { ...b, height: 410 })).toBe(false);
  });

  it('compareBoardSnapshots reports matching lite/regular geometry', () => {
    const regular = makeSnapshot();
    const lite = makeSnapshot({
      mode: { isLite: true, isCanvas: true, isCompact: false },
      canvas: { x: 14, y: 114, width: 532, height: 652 },
      content: { x: 14, y: 114, width: 532, height: 652 },
    });
    const result = compareBoardSnapshots(regular, lite);
    expect(result.ok).toBe(true);
    expect(result.diffs).toEqual([]);
  });

  it('compareBoardSnapshots skips inner grid when canvas vs DOM', () => {
    const regular = makeSnapshot();
    const lite = makeSnapshot({
      mode: { isLite: true, isCanvas: true, isCompact: false },
      canvas: { x: 80, y: 90, width: 400, height: 600 },
    });
    const result = compareBoardSnapshots(regular, lite);
    expect(result.ok).toBe(true);
    expect(result.diffs).toEqual([]);
  });

  it('compareBoardSnapshots reports board size drift', () => {
    const a = makeSnapshot();
    const b = makeSnapshot({
      board: { x: 0, y: 100, width: 500, height: 680 },
    });
    const result = compareBoardSnapshots(a, b);
    expect(result.ok).toBe(false);
    expect(result.diffs.some((d) => d.startsWith('board:'))).toBe(true);
  });

  it('assertBoardLayout passes desktop regular snapshot', () => {
    const result = assertBoardLayout(makeSnapshot(), 'desktop-regular');
    expect(result.ok).toBe(true);
    expect(result.errors).toEqual([]);
  });

  it('assertBoardLayout passes mobile lite snapshot', () => {
    const result = assertBoardLayout(
      makeSnapshot({
        viewport: { width: 390, height: 760 },
        mode: { isLite: true, isCanvas: true, isCompact: true },
        contentInsetTop: 0,
        contentInsetBottom: 0,
        canvas: { x: 0, y: 100, width: 360, height: 620 },
        content: { x: 0, y: 100, width: 360, height: 620 },
        fortTopVisible: null,
        fortBottomVisible: null,
      }),
      'mobile-lite',
    );
    expect(result.ok).toBe(true);
  });

  it('assertBoardLayout fails on overflow and player bar overlap', () => {
    const result = assertBoardLayout(
      makeSnapshot({
        boardOverflowsSlot: true,
        overlapsTopBar: true,
        gapBelowTopBar: 8,
      }),
      'desktop-regular',
    );
    expect(result.ok).toBe(false);
    expect(result.errors).toContain('board overflows slot');
    expect(result.errors).toContain('board overlaps top player bar');
  });

  it('assertBoardLayout passes tutorial mobile regular snapshot', () => {
    const result = assertBoardLayout(
      makeSnapshot({
        viewport: { width: 390, height: 760 },
        mode: { isLite: false, isCanvas: false, isCompact: true },
        topBar: null,
        bottomBar: null,
        gapBelowTopBar: null,
        gapAboveBottomBar: null,
        overlapsTopBar: null,
        contentInsetTop: 0,
        contentInsetBottom: 0,
        heightUnits: '13.16',
        boardFlexShrink: '1',
      }),
      'tutorial-mobile-regular',
    );
    expect(result.ok).toBe(true);
  });

  it('readBoardLayoutSnapshot returns null without board', () => {
    const doc = document.implementation.createHTMLDocument('test');
    expect(readBoardLayoutSnapshot(doc)).toBeNull();
  });
});
