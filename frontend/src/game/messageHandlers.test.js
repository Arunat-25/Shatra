import { describe, expect, it, vi } from 'vitest';
import { dispatchServerMessage } from './messageHandlers';
import { GAME_ACTIONS } from './actions';

function collectDispatches(payload, modeAi = false, myColor = 'белый') {
  const calls = [];
  const dispatch = (action) => calls.push(action);
  const msg = dispatchServerMessage(
    payload,
    dispatch,
    modeAi,
    () => myColor,
  );
  return { calls, msg };
}

describe('dispatchServerMessage', () => {
  it('game_over dispatches GAME_OVER', () => {
    const { calls } = collectDispatches({
      game_over: true,
      winner: 'белый',
      reason: 'resign',
    });
    expect(calls.some((c) => c.type === GAME_ACTIONS.GAME_OVER)).toBe(true);
  });

  it('timer_tick updates clocks', () => {
    const { calls } = collectDispatches({
      type: 'timer_tick',
      time: { белый: 60, черный: 55 },
    });
    expect(calls).toEqual([
      { type: GAME_ACTIONS.TIMER_TICK, payload: { белый: 60, черный: 55 } },
    ]);
  });

  it('rematch_status sets ready flags', () => {
    const { calls } = collectDispatches({
      status: 'rematch_status',
      self_ready: true,
      opponent_ready: false,
    });
    expect(calls[0].type).toBe(GAME_ACTIONS.SET_REMATCH_STATUS);
    expect(calls[0].payload.opponent_ready).toBe(false);
  });

  it('rematch_cancelled marks unavailable', () => {
    const { calls } = collectDispatches({
      status: 'rematch_cancelled',
      message: 'Соперник вышел',
    });
    expect(calls[0].type).toBe(GAME_ACTIONS.SET_REMATCH_UNAVAILABLE);
  });

  it('move in AI mode sets aiThinking when not my turn', () => {
    const { calls } = collectDispatches(
      {
        message: 'Ход',
        desk: { '10': 'черный бий' },
        movers_color: 'черный',
        game_over: false,
      },
      true,
      'белый',
    );
    const move = calls.find((c) => c.type === GAME_ACTIONS.MOVE_MADE);
    expect(move.payload.aiThinking).toBe(true);
  });

  it('server error returns error text', () => {
    const { msg } = collectDispatches({ status: 'error', message: 'Нельзя' });
    expect(msg.type).toBe('error');
    expect(msg.text).toBe('Нельзя');
  });
});
