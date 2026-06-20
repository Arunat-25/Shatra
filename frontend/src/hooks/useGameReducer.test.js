import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useGameReducer, { GAME_ACTIONS } from './useGameReducer';

vi.mock('../game/messageHandlers', () => ({
  dispatchServerMessage: vi.fn(() => ({ text: 'Ход сделан', type: 'info' })),
}));

vi.mock('../audio/playGameSound', () => ({
  playForAction: vi.fn(),
  playForServerError: vi.fn(),
}));

import { dispatchServerMessage } from '../game/messageHandlers';

describe('useGameReducer handleServerMessage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('suppresses toast when server confirms optimistic move', () => {
    const { result } = renderHook(() => useGameReducer(false, () => 'белый'));

    act(() => {
      result.current.dispatch({
        type: GAME_ACTIONS.OPTIMISTIC_MOVE,
        payload: { result: { capturedPositions: [] }, from: 11, to: 19, ply: 1 },
      });
    });

    let msg;
    act(() => {
      msg = result.current.handleServerMessage({
        from_pos: 11,
        to_pos: 19,
        movers_color: 'белый',
        message_code: 'turn.now',
        ply: 1,
      });
    });

    expect(dispatchServerMessage).toHaveBeenCalled();
    expect(msg).toBeNull();
  });

  it('shows toast for opponent move', () => {
    const { result } = renderHook(() => useGameReducer(false, () => 'белый'));

    let msg;
    act(() => {
      msg = result.current.handleServerMessage({
        from_pos: 11,
        to_pos: 19,
        movers_color: 'черный',
        message_code: 'turn.now',
        ply: 1,
      });
    });

    expect(msg).toEqual({ text: 'Ход сделан', type: 'info' });
  });

  it('suppresses rematch toast when already ready optimistically (H9)', () => {
    vi.mocked(dispatchServerMessage).mockReturnValueOnce({
      text: 'Ожидание согласия соперника на реванш…',
      type: 'info',
    });
    const { result } = renderHook(() => useGameReducer(false, () => 'белый'));

    act(() => {
      result.current.dispatch({
        type: GAME_ACTIONS.SET_REMATCH_STATUS,
        payload: { self_ready: true, opponent_ready: false },
      });
    });

    let msg;
    act(() => {
      msg = result.current.handleServerMessage({
        status: 'rematch_status',
        self_ready: true,
        opponent_ready: false,
      });
    });

    expect(msg).toBeNull();
  });
});
