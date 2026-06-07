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
    myColor: 'белый',
    moversColor: 'белый',
    moveFrom: 19,
    posForMandatoryCapture: 19,
    board: {
      19: 'белый бий',
      33: null,
      10: 'белый бий',
    },
  };

  it('sends move from chain cell when clicking capture target only', () => {
    const { hookProps, send, deselectPiece } = makeDeps(chainState);
    const { result } = renderHook(() => useCellClick(hookProps));

    act(() => {
      result.current(33);
    });

    expect(send).toHaveBeenCalledTimes(1);
    expect(send.mock.calls[0][0]).toMatchObject({
      move_from: 'position19',
      move_to: 'position33',
      position_for_mandatory_capture: 19,
    });
    expect(deselectPiece).not.toHaveBeenCalled();
  });

  it('refreshes hints when clicking the active chain piece', () => {
    const { hookProps, send } = makeDeps(chainState);
    const { result } = renderHook(() => useCellClick(hookProps));

    act(() => {
      result.current(19);
    });

    expect(send).toHaveBeenCalledTimes(1);
    expect(send.mock.calls[0][0]).toMatchObject({
      position: 'position19',
      position_for_mandatory_capture: 19,
    });
  });

  it('ignores selecting another own piece during chain', () => {
    const { hookProps, send } = makeDeps(chainState);
    const { result } = renderHook(() => useCellClick(hookProps));

    act(() => {
      result.current(10);
    });

    expect(send).not.toHaveBeenCalled();
  });
});

describe('useCellClick normal moves', () => {
  it('selects piece on first click and sends move on second', () => {
    const state = {
      myColor: 'белый',
      moversColor: 'белый',
      moveFrom: null,
      posForMandatoryCapture: null,
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
    });

    hookProps.stateRef.current = { ...state, moveFrom: 10 };
    rerender(hookProps);

    act(() => {
      result.current(14);
    });
    expect(send).toHaveBeenCalledWith(expect.objectContaining({
      move_from: 'position10',
      move_to: 'position14',
    }));
    expect(deselectPiece).toHaveBeenCalledTimes(1);
  });
});
