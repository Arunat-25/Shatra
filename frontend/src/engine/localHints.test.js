import { describe, expect, it } from 'vitest';
import { computeLocalHints } from './localHints';

function emptyBoard() {
  return Object.fromEntries(Array.from({ length: 62 }, (_, i) => [i + 1, null]));
}

describe('computeLocalHints', () => {
  it('returns legal targets for black shatra on cell 11', () => {
    const board = emptyBoard();
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

  it('highlights landing cells and captured enemy for batyr jump over 55', () => {
    const board = emptyBoard();
    board[61] = 'черный батыр';
    board[55] = 'белая шатра';

    const { essential, captured } = computeLocalHints({
      board,
      moversColor: 'черный',
      posForMandatoryCapture: null,
      batyrCapturedThisTurn: [],
    }, 61);

    expect(essential).toContain(53);
    expect(essential).toContain(49);
    expect(captured).toEqual([55]);
  });
});
