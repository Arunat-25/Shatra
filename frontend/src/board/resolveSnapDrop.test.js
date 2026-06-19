import { describe, expect, it } from 'vitest';
import { resolveSnapDrop } from './resolveSnapDrop';

const bounds = {
  10: { left: 80, top: 80, right: 120, bottom: 120 },
  20: { left: 180, top: 80, right: 220, bottom: 120 },
};

function getCellBounds(id) {
  return bounds[id] ?? null;
}

describe('resolveSnapDrop', () => {
  it('places when piece overlaps legal cell even if cursor is elsewhere', () => {
    const target = resolveSnapDrop({
      clientX: 100,
      clientY: 100,
      from: 10,
      legalDests: [20],
      resolveCellAt: () => 10,
      getCellBounds,
      ghost: { x: 195, y: 100, size: 40 },
    });
    expect(target).toBe(20);
  });

  it('places when cursor is inside legal cell bounds', () => {
    const target = resolveSnapDrop({
      clientX: 190,
      clientY: 95,
      from: 10,
      legalDests: new Set([20]),
      resolveCellAt: () => null,
      getCellBounds,
    });
    expect(target).toBe(20);
  });

  it('does not place when neither cursor nor piece touch legal cell', () => {
    const target = resolveSnapDrop({
      clientX: 100,
      clientY: 100,
      from: 10,
      legalDests: [20],
      resolveCellAt: () => 10,
      getCellBounds,
      ghost: { x: 100, y: 100, size: 40 },
    });
    expect(target).toBeNull();
  });
});
