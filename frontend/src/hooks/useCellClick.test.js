import { describe, expect, it, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useCellClick from './useCellClick';
import { GAME_ACTIONS } from '../game/actions';

function makeDeps(state, overrides = {}) {
  const dispatch = vi.fn();
  const send = vi.fn(() => true);
  const deselectPiece = vi.fn();
  const showMessage = vi.fn();
  const stateRef = { current: state };
  return {
    dispatch,
    send,
    deselectPiece,
    showMessage,
    stateRef,
    hookProps: {
      stateRef,
      dispatch,
      send,
      deselectPiece,
      showMessage,
      isBlocked: false,
      ...overrides,
    },
  };
}

describe('useCellClick capture chain', () => {
  const chainState = {
    myColor: 'черный',
    moversColor: 'черный',
    moveFrom: 25,
    posForMandatoryCapture: 25,
    batyrCapturedThisTurn: [],
    board: {
      25: 'черная шатра',
      32: 'белая шатра',
      39: null,
    },
  };

  it('sends move from chain cell when clicking capture target only', () => {
    const { hookProps, send, deselectPiece, dispatch } = makeDeps(chainState);
    const { result } = renderHook(() => useCellClick(hookProps));

    act(() => {
      result.current(39);
    });

    expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({ type: GAME_ACTIONS.OPTIMISTIC_MOVE }),
    );
    expect(send).toHaveBeenCalledTimes(1);
    expect(send.mock.calls[0][0]).toMatchObject({
      v: 2,
      t: 'move',
      from: 25,
      to: 39,
    });
    expect(deselectPiece).not.toHaveBeenCalled();
  });

  it('refreshes hints locally when clicking the active chain piece', () => {
    const { hookProps, send, dispatch } = makeDeps(chainState);
    const { result } = renderHook(() => useCellClick(hookProps));

    act(() => {
      result.current(25);
    });

    expect(send).not.toHaveBeenCalled();
    expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({ type: GAME_ACTIONS.HIGHLIGHTS }),
    );
  });

  it('ignores selecting another own piece during chain', () => {
    const withExtra = {
      ...chainState,
      board: { ...chainState.board, 20: 'черная шатра' },
    };
    const { hookProps, send } = makeDeps(withExtra);
    const { result } = renderHook(() => useCellClick(hookProps));

    act(() => {
      result.current(20);
    });

    expect(send).not.toHaveBeenCalled();
  });
});

describe('useCellClick normal moves', () => {
  it('applies local highlights on piece select (no hint WS)', () => {
    const state = {
      myColor: 'белый',
      moversColor: 'белый',
      moveFrom: null,
      posForMandatoryCapture: null,
      batyrCapturedThisTurn: [],
      board: { 53: 'белая шатра' },
    };
    const { hookProps, send, dispatch } = makeDeps(state);
    const { result } = renderHook(() => useCellClick(hookProps));

    act(() => {
      result.current(53);
    });

    expect(send).not.toHaveBeenCalled();
    expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({
        type: GAME_ACTIONS.SET_MOVE_FROM,
        payload: 53,
        highlights: expect.objectContaining({
          essential: expect.any(Array),
        }),
      }),
    );
  });

  it('selects piece on first click and sends move on second', () => {
    const state = {
      myColor: 'белый',
      moversColor: 'белый',
      moveFrom: null,
      posForMandatoryCapture: null,
      batyrCapturedThisTurn: [],
      board: { 10: 'белый бий', 14: null },
    };
    const { hookProps, dispatch, send, deselectPiece } = makeDeps(state);
    const { result, rerender } = renderHook((props) => useCellClick(props), {
      initialProps: hookProps,
    });

    act(() => {
      result.current(10);
    });
    expect(dispatch).toHaveBeenCalledWith({
      type: GAME_ACTIONS.SET_MOVE_FROM,
      payload: 10,
      highlights: expect.objectContaining({
        essential: expect.any(Array),
      }),
    });

    hookProps.stateRef.current = { ...state, moveFrom: 10 };
    rerender(hookProps);

    act(() => {
      result.current(14);
    });
    expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({ type: GAME_ACTIONS.OPTIMISTIC_MOVE }),
    );
    expect(send).toHaveBeenCalledWith(expect.objectContaining({
      v: 2,
      t: 'move',
      from: 10,
      to: 14,
    }));
    expect(deselectPiece).toHaveBeenCalledTimes(1);
  });
});
