import { describe, expect, it } from 'vitest';
import { gameReducer, initialGameState } from './reducer';
import { GAME_ACTIONS } from './actions';

describe('gameReducer', () => {
  it('GAME_OVER locks board and stores reason', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.GAME_OVER,
      payload: { winner: 'белый', reason: 'timeout', desk: { 10: 'черный бий' } },
    });
    expect(next.gameOver).toBe(true);
    expect(next.gameOverReason).toBe('timeout');
    expect(next.winner).toBe('белый');
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
});
