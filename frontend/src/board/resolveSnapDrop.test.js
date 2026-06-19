import { describe, expect, it } from 'vitest';
import { resolveSnapDrop } from './resolveSnapDrop';

const centers = {
  10: { x: 100, y: 100, size: 40 },
  20: { x: 200, y: 100, size: 40 },
  30: { x: 300, y: 100, size: 40 },
};

function getCellCenter(id) {
  return centers[id] ?? null;
}

describe('resolveSnapDrop', () => {
  it('prefers legal cell when pointer is inside its bounds', () => {
    const target = resolveSnapDrop({
      clientX: 215,
      clientY: 108,
      from: 10,
      legalDests: new Set([20]),
      resolveCellAt: () => null,
      getCellCenter,
    });
    expect(target).toBe(20);
  });

  it('snaps to nearest legal cell within radius when pointer is in a gap', () => {
    const target = resolveSnapDrop({
      clientX: 200,
      clientY: 130,
      from: 10,
      legalDests: [20],
      resolveCellAt: () => null,
      getCellCenter,
    });
    expect(target).toBe(20);
  });

  it('does not snap to illegal cells', () => {
    const target = resolveSnapDrop({
      clientX: 305,
      clientY: 100,
      from: 10,
      legalDests: [20],
      resolveCellAt: () => 30,
      getCellCenter,
    });
    expect(target).toBeNull();
  });

  it('uses resolveCellAt when it matches a legal dest', () => {
    const target = resolveSnapDrop({
      clientX: 0,
      clientY: 0,
      from: 10,
      legalDests: [20],
      resolveCellAt: () => 20,
      getCellCenter,
    });
    expect(target).toBe(20);
  });
});
