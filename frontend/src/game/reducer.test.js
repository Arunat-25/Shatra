import { describe, expect, it } from 'vitest';
import { gameReducer, initialGameState } from './reducer';
import { GAME_ACTIONS } from './actions';

describe('gameReducer', () => {
  it('GAME_OVER locks board and stores winner_color', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.GAME_OVER,
      payload: { winner_color: 'белый', reason: 'timeout', desk: { 10: 'черный бий' } },
    });
    expect(next.gameOver).toBe(true);
    expect(next.gameOverReason).toBe('timeout');
    expect(next.winnerColor).toBe('белый');
  });

  it('GAME_CANCELLED stores message_code', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.GAME_CANCELLED,
      payload: { message_code: 'cancel.you' },
    });
    expect(next.gameOver).toBe(true);
    expect(next.gameOverReason).toBe('cancelled');
    expect(next.gameOverMessageCode).toBe('cancel.you');
    expect(next.winnerColor).toBe('');
  });

  it('OPPONENT_DISCONNECTED sets countdown', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.OPPONENT_DISCONNECTED,
      payload: { timeout: 30 },
    });
    expect(next.opponentDisconnected).toBe(true);
    expect(next.disconnectTimeout).toBe(30);
  });

  it('SET_REMATCH_STATUS tracks both sides', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.SET_REMATCH_STATUS,
      payload: { self_ready: true, opponent_ready: true },
    });
    expect(next.rematchReady).toBe(true);
    expect(next.rematchOpponentReady).toBe(true);
  });

  it('GAME_STARTED clears waiting', () => {
    const next = gameReducer(
      { ...initialGameState, waiting: true },
      {
        type: GAME_ACTIONS.GAME_STARTED,
        payload: {
          desk: { 10: 'черный бий' },
          movers_color: 'белый',
          your_color: 'белый',
        },
      },
    );
    expect(next.waiting).toBe(false);
    expect(next.myColor).toBe('белый');
  });

  it('keeps captured pieces visible while capture chain continues', () => {
    const state = {
      ...initialGameState,
      board: {
        20: 'белая шатра',
        28: 'черная шатра',
      },
    };

    const pending = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 36: 'белая шатра' },
        captured_positions: [28],
        position_for_mandatory_capture: 36,
      },
    });

    expect(pending.capturedGhostPieces).toEqual({ 28: 'черная шатра' });

    const finished = gameReducer(pending, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 52: 'белая шатра' },
        captured_positions: [44],
        position_for_mandatory_capture: null,
      },
    });

    expect(finished.capturedGhostPieces).toEqual({});
  });
});
