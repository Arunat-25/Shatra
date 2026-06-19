import { describe, expect, it } from 'vitest';
import { computeLocalHints } from './localHints';

describe('computeLocalHints', () => {
  it('returns legal targets for black shatra on cell 11', () => {
    const board = Object.fromEntries(
      Array.from({ length: 62 }, (_, i) => [i + 1, null]),
    );
    board[11] = 'черная шатра';

    const { essential } = computeLocalHints({
      board,
      moversColor: 'черный',
      posForMandatoryCapture: null,
      batyrCapturedThisTurn: [],
    }, 11);

    expect(essential).toContain(12);
    expect(essential).toContain(18);
  });
});
