import { useCallback } from 'react';
import { GAME_ACTIONS } from '../game/actions';
import { MSG_WARNING } from '../constants';
import { getPieceColor } from '../utils';
import { buildMovePayload } from '../utils/wsPayloads';
import { computeLocalHints } from '../engine/localHints';
import { applyLocalMove } from '../engine/localMove';
import i18n from '../i18n';

function chainCaptureCell(state) {
  const pos = state.posForMandatoryCapture;
  return pos != null ? Number(pos) : null;
}

function applyLocalHighlights(dispatch, state, fromCell) {
  const { essential, captured } = computeLocalHints(state, fromCell);
  dispatch({
    type: GAME_ACTIONS.HIGHLIGHTS,
    payload: { essential, captured },
  });
}

export default function useCellClick({
  stateRef,
  dispatch,
  send,
  deselectPiece,
  showMessage,
  isBlocked,
}) {
  const selectPiece = useCallback((positionNum) => {
    dispatch({ type: GAME_ACTIONS.SET_MOVE_FROM, payload: positionNum });
    applyLocalHighlights(dispatch, stateRef.current, positionNum);
  }, [dispatch, stateRef]);

  const trySendMove = useCallback((from, to, { deselect = false } = {}) => {
    const s = stateRef.current;
    const wsPayload = buildMovePayload(s, from, to);
    const { ok, result } = applyLocalMove(s, from, to);
    if (!ok) return false;

    dispatch({
      type: GAME_ACTIONS.OPTIMISTIC_MOVE,
      payload: { result, from, to, ply: wsPayload.ply },
    });

    if (!send(wsPayload)) {
      dispatch({ type: GAME_ACTIONS.ROLLBACK_OPTIMISTIC });
      showMessage(i18n.t('game.connectionLost'), MSG_WARNING);
      return false;
    }

    if (deselect) deselectPiece();
    return true;
  }, [stateRef, dispatch, send, deselectPiece, showMessage]);

  return useCallback((positionNum) => {
    if (isBlocked) return;
    const s = stateRef.current;

    if (s.moversColor !== s.myColor) {
      showMessage(i18n.t('game.notYourTurn'), MSG_WARNING);
      return;
    }

    const chainCell = chainCaptureCell(s);
    if (chainCell != null) {
      if (positionNum === chainCell) {
        applyLocalHighlights(dispatch, s, chainCell);
        return;
      }

      const targetPiece = s.board[positionNum];
      if (targetPiece && getPieceColor(targetPiece) === s.myColor) {
        return;
      }

      if (!trySendMove(chainCell, positionNum)) {
        return;
      }
      return;
    }

    if (s.moveFrom === null) {
      const piece = s.board[positionNum];
      if (!piece || getPieceColor(piece) !== s.myColor) return;
      selectPiece(positionNum);
      return;
    }

    if (s.moveFrom === positionNum) {
      deselectPiece();
      return;
    }

    const targetPiece = s.board[positionNum];
    if (targetPiece && getPieceColor(targetPiece) === s.myColor) {
      selectPiece(positionNum);
      return;
    }

    if (!trySendMove(s.moveFrom, positionNum, { deselect: true })) {
      return;
    }
  }, [isBlocked, stateRef, showMessage, selectPiece, deselectPiece, trySendMove, dispatch]);
}
