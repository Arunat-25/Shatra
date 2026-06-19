import { describe, expect, it } from 'vitest';
import {
  classifyIncomingPly,
  nextOutgoingPly,
  outstandingPlyCount,
  pendingAfterConfirm,
  isMoveConfirmation,
} from './syncLayer';

describe('classifyIncomingPly', () => {
  it('applies next ply', () => {
    expect(classifyIncomingPly(2, 3)).toBe('apply');
  });

  it('ignores stale', () => {
    expect(classifyIncomingPly(3, 3)).toBe('stale');
    expect(classifyIncomingPly(4, 2)).toBe('stale');
  });

  it('detects gap', () => {
    expect(classifyIncomingPly(2, 5)).toBe('gap');
  });

  it('legacy without ply', () => {
    expect(classifyIncomingPly(2, null)).toBe('legacy');
  });
});

describe('nextOutgoingPly', () => {
  it('accounts for pending queue', () => {
    expect(nextOutgoingPly({ confirmedPly: 1, pendingMoves: [{ ply: 2 }] })).toBe(3);
    expect(nextOutgoingPly({ confirmedPly: 1, pendingMove: { ply: 2 } })).toBe(3);
  });
});

describe('pendingAfterConfirm', () => {
  it('clears matching pending', () => {
    const state = {
      pendingMoves: [{ ply: 2, from: 1, to: 2 }, { ply: 3, from: 3, to: 4 }],
      rollbackSnapshot: { board: {} },
    };
    expect(pendingAfterConfirm(state, 2)).toEqual({
      pendingMoves: [{ ply: 3, from: 3, to: 4 }],
      pendingMove: { ply: 3, from: 3, to: 4 },
      rollbackSnapshot: { board: {} },
    });
  });
});

describe('isMoveConfirmation', () => {
  it('detects delta move payloads', () => {
    expect(isMoveConfirmation({ from_pos: 1, to_pos: 2, message_code: 'turn.now' })).toBe(true);
    expect(isMoveConfirmation({ desk: {}, message_code: 'x' })).toBe(false);
  });
});
