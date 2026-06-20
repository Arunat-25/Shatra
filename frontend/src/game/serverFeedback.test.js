import { describe, expect, it } from 'vitest';
import { GAME_ACTIONS } from './actions';
import {
  FEEDBACK_SCENARIOS,
  shouldSuppressActionSound,
  shouldSuppressServerToast,
} from './serverFeedback';

describe('FEEDBACK_SCENARIOS', () => {
  it('covers all documented duplicate-feedback paths', () => {
    const ids = FEEDBACK_SCENARIOS.map((s) => s.id);
    expect(ids).toEqual([
      'move_confirm',
      'resync_snapshot',
      'rematch_status_echo',
      'cancel_echo',
    ]);
  });
});

describe('shouldSuppressServerToast', () => {
  it('move_confirm: own move confirmation', () => {
    const state = { pendingMove: { ply: 1 }, myColor: 'белый' };
    expect(shouldSuppressServerToast(
      { from_pos: 11, to_pos: 19, movers_color: 'белый', message_code: 'turn.now', ply: 1 },
      state,
      'белый',
    )).toBe(true);
  });

  it('rematch_status_echo: self already ready', () => {
    expect(shouldSuppressServerToast(
      { status: 'rematch_status', self_ready: true, opponent_ready: false },
      { rematchReady: true, rematchOpponentReady: false },
      'белый',
    )).toBe(true);
  });

  it('allows opponent move toast', () => {
    expect(shouldSuppressServerToast(
      { from_pos: 11, to_pos: 19, movers_color: 'черный', message_code: 'turn.now', ply: 1 },
      { pendingMove: null },
      'белый',
    )).toBe(false);
  });
});

describe('shouldSuppressActionSound', () => {
  it('resync_snapshot: no game-start sound', () => {
    expect(shouldSuppressActionSound(
      { type: GAME_ACTIONS.GAME_STARTED, payload: { _resync: true } },
      {},
      'белый',
    )).toBe(true);
  });

  it('cancel_echo: no second cancel sound', () => {
    expect(shouldSuppressActionSound(
      { type: GAME_ACTIONS.GAME_CANCELLED, payload: { message_code: 'cancel.you' } },
      { gameOver: true, gameOverReason: 'cancelled' },
      'белый',
    )).toBe(true);
  });

  it('move_confirm: skip confirm sound', () => {
    expect(shouldSuppressActionSound(
      { type: GAME_ACTIONS.MOVE_MADE, payload: { from_pos: 11, to_pos: 19, movers_color: 'белый' } },
      { pendingMove: { ply: 1 }, myColor: 'белый' },
      'белый',
    )).toBe(true);
  });
});
