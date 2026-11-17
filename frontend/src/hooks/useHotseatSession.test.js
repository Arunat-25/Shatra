import { describe, expect, it, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { GAME_ACTIONS } from './useGameReducer';
import useHotseatSession from './useHotseatSession';

function makeDeps() {
  const dispatched = [];
  const consumed = [];
  const myColorRef = { current: null };
  const deps = {
    enabled: true,
    myColorRef,
    state: { board: {} },
    dispatch: (action) => dispatched.push(action),
    handleServerMessage: (message) => {
      consumed.push(message);
      return null;
    },
    showMessage: vi.fn(),
    navigate: vi.fn(),
  };
  return { deps, dispatched, consumed, myColorRef };
}

describe('useHotseatSession', () => {
  it('starts the game immediately without waiting', () => {
    const { deps, dispatched, consumed, myColorRef } = makeDeps();
    renderHook(() => useHotseatSession(deps));

    // Хук отдаёт game_started в handleServerMessage (редьюсер диспетчит
    // GAME_STARTED) и сам выставляет цвет под текущего игрока.
    expect(consumed).toHaveLength(1);
    expect(consumed[0].status).toBe('game_started');
    expect(dispatched.map((a) => a.type)).toEqual([GAME_ACTIONS.SET_MY_COLOR]);
    expect(myColorRef.current).toBe('белый');
  });

  it('passes moves through the referee into the reducer pipeline', () => {
    const { deps, dispatched, consumed, myColorRef } = makeDeps();
    const { result } = renderHook(() => useHotseatSession(deps));

    act(() => {
      result.current.send({ t: 'move', from: 40, to: 32 });
    });

    const moveMsg = consumed.find((m) => m.from_pos === 40);
    expect(moveMsg).toBeDefined();
    expect(moveMsg.movers_color).toBe('черный');
    expect(dispatched.map((a) => a.type)).toContain(GAME_ACTIONS.SET_MY_COLOR);
    expect(myColorRef.current).toBe('черный');
  });

  it('delivers resign as game over and rematch as a fresh game', () => {
    const { deps, dispatched, consumed, myColorRef } = makeDeps();
    const { result } = renderHook(() => useHotseatSession(deps));

    act(() => {
      result.current.send({ t: 'resign' });
    });
    const gameOverMsg = consumed.find((m) => m.game_over);
    expect(gameOverMsg.reason).toBe('resign');
    expect(gameOverMsg.winner_color).toBe('черный');

    act(() => {
      result.current.send({ t: 'request_rematch' });
    });
    const starts = consumed.filter((m) => m.status === 'game_started');
    expect(starts).toHaveLength(2);
    expect(starts[1].ply).toBe(0);
    expect(myColorRef.current).toBe('белый');
    expect(dispatched.at(-1).type).toBe(GAME_ACTIONS.SET_MY_COLOR);
    expect(dispatched.at(-1).payload).toBe('белый');
  });
});
