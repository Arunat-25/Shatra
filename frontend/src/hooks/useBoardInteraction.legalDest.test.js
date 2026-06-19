import { describe, expect, it } from 'vitest';

/**
 * Mirrors finishDrag legal check bug: activeLegalDests must be passed explicitly
 * after dragLegalDestsRef is cleared.
 */
function isLegalDest(cellId, dests) {
  if (cellId == null || !dests) return false;
  if (dests instanceof Set) return dests.has(cellId);
  return dests.includes(cellId);
}

describe('drag drop legal dest check', () => {
  it('accepts target from snapshotted legal set after ref cleared', () => {
    const activeLegalDests = new Set([27]);
    const clearedRef = null;
    const staleProp = new Set();

    expect(isLegalDest(27, activeLegalDests)).toBe(true);
    expect(isLegalDest(27, clearedRef ?? staleProp)).toBe(false);
  });
});
