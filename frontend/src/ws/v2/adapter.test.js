import { describe, expect, it } from 'vitest';
import { adaptV2ServerMessage } from './adapter.js';
import { applyMoveDelta } from './applyDelta.js';
import { nextClientPly } from './payloads.js';

describe('v2 applyMoveDelta', () => {
  it('moves piece and removes captured cells', () => {
    const board = { 20: 'белая шатра', 28: 'черная шатра', 36: null };
    const next = applyMoveDelta(board, { from: 20, to: 36, captured: [28] });
    expect(next[20]).toBeNull();
    expect(next[28]).toBeNull();
    expect(next[36]).toBe('белая шатра');
  });
});

describe('v2 adapter', () => {
  it('converts snapshot to game_started shape', () => {
    const adapted = adaptV2ServerMessage({
      v: 2,
      t: 'snapshot',
      ply: 3,
      turn: 'белый',
      board: { '10': 'белый бий' },
      yourColor: 'белый',
      chainCell: null,
      batyrCaptured: [],
      moveHistory: [],
    });
    expect(adapted.status).toBe('game_started');
    expect(adapted.ply).toBe(3);
    expect(adapted.your_color).toBe('белый');
  });

  it('converts move delta using previous board', () => {
    const adapted = adaptV2ServerMessage(
      {
        v: 2,
        t: 'move',
        ply: 1,
        from: 45,
        to: 37,
        turn: 'черный',
        captured: [],
        chainCell: null,
        messageCode: 'turn.now',
      },
      { board: { 45: 'белый бий', 37: null } },
    );
    expect(adapted.from_pos).toBe(45);
    expect(adapted.to_pos).toBe(37);
    expect(adapted.desk[37]).toBe('белый бий');
    expect(adapted.ply).toBe(1);
    expect(adapted.position_for_mandatory_capture).toBeNull();
  });

  it('omits chainCell on turn switch even when engine had mandatory pos', () => {
    const adapted = adaptV2ServerMessage(
      {
        v: 2,
        t: 'move',
        from: 28,
        to: 36,
        turn: 'белый',
        captured: [],
        messageCode: 'turn.now',
      },
      { board: { 28: 'черная шатра', 36: null } },
    );
    expect(adapted.movers_color).toBe('белый');
    expect(adapted.position_for_mandatory_capture).toBeNull();
  });
});

describe('nextClientPly', () => {
  it('accounts for pending optimistic move', () => {
    expect(nextClientPly({ confirmedPly: 2, pendingMove: null })).toBe(3);
    expect(nextClientPly({ confirmedPly: 2, pendingMove: { from: 1, to: 2 } })).toBe(4);
  });
});
