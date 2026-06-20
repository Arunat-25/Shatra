import { describe, expect, it } from 'vitest';
import { adaptV2ServerMessage } from './adapter.js';
import { applyMoveDelta } from './applyDelta.js';
import { nextClientPly } from './payloads.js';
import { gameReducer, initialGameState } from '../../game/reducer.js';
import { GAME_ACTIONS } from '../../game/actions.js';

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
    expect(adapted._resync).toBeFalsy();
  });

  it('sync snapshot sets resync flag (H8)', () => {
    const adapted = adaptV2ServerMessage({
      v: 2,
      t: 'snapshot',
      resync: true,
      ply: 5,
      turn: 'черный',
      board: { '10': 'белый бий' },
      yourColor: 'белый',
      chainCell: null,
      batyrCaptured: [],
      moveHistory: [],
    });
    expect(adapted._resync).toBe(true);
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

  it('rematch_status v2 envelope maps to handler shape', () => {
    const adapted = adaptV2ServerMessage({
      v: 2,
      t: 'rematch_status',
      self_ready: true,
      opponent_ready: false,
    });
    expect(adapted.status).toBe('rematch_status');
    expect(adapted.self_ready).toBe(true);
    expect(adapted.opponent_ready).toBe(false);
  });

  it('draw_declined v2 envelope maps to handler shape', () => {
    const adapted = adaptV2ServerMessage({
      v: 2,
      t: 'draw_declined',
      message_code: 'draw.opponent_declined',
    });
    expect(adapted.status).toBe('draw_declined');
    expect(adapted.message_code).toBe('draw.opponent_declined');
  });

  it('reject with snapshot exposes resync payload with chain and batyr (H22)', () => {
    const snapshot = {
      v: 2,
      t: 'snapshot',
      ply: 5,
      turn: 'черный',
      board: { '8': 'черный батыр', '10': null, '14': null },
      yourColor: 'белый',
      chainCell: 8,
      batyrCaptured: [10],
      moveHistory: [],
    };
    const adapted = adaptV2ServerMessage({
      v: 2,
      t: 'reject',
      code: 'move.impossible',
      snapshot,
    });
    expect(adapted.status).toBe('error');
    expect(adapted._v2Resync.status).toBe('game_started');
    expect(adapted._v2Resync._resync).toBe(true);
    expect(adapted._v2Resync.position_for_mandatory_capture).toBe(8);
    expect(adapted._v2Resync.captured_pieces).toEqual([10]);

    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.GAME_STARTED,
      payload: adapted._v2Resync,
    });
    expect(next.posForMandatoryCapture).toBe(8);
    expect(next.batyrCapturedThisTurn).toEqual([10]);
    expect(next.moversColor).toBe('черный');
  });

  it('pass move delta keeps board unchanged (H24)', () => {
    const board = { 19: 'белый бий', 10: 'белый бий' };
    const adapted = adaptV2ServerMessage(
      {
        v: 2,
        t: 'move',
        ply: 2,
        from: 0,
        to: 0,
        turn: 'черный',
        captured: [],
        canPass: false,
        chainCell: null,
        batyrCaptured: [],
        messageCode: 'move.passed',
      },
      { board },
    );
    expect(adapted.desk).toEqual(board);
    expect(adapted.from_pos).toBe(0);
    expect(adapted.to_pos).toBe(0);
  });
});

describe('nextClientPly', () => {
  it('accounts for pending optimistic move', () => {
    expect(nextClientPly({ confirmedPly: 2, pendingMove: null })).toBe(3);
    expect(nextClientPly({ confirmedPly: 2, pendingMove: { from: 1, to: 2 } })).toBe(4);
  });
});
