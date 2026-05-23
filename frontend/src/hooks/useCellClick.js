import { useCallback } from 'react';
import { GAME_ACTIONS } from '../game/actions';
import { MSG_WARNING } from '../constants';
import { getPieceColor } from '../utils';
import { buildHintPayload, buildMovePayload } from '../utils/wsPayloads';

export default function useCellClick({
  stateRef,
  dispatch,
  send,
  deselectPiece,
  showMessage,
  isBlocked,
}) {
  const selectPiece = useCallback((positionNum, s) => {
    dispatch({ type: GAME_ACTIONS.SET_MOVE_FROM, payload: positionNum });
    send(buildHintPayload(s, positionNum));
  }, [dispatch, send]);

  return useCallback((positionNum) => {
    if (isBlocked) return;
    const s = stateRef.current;

    if (s.moversColor !== s.myColor) {
      showMessage('Не ваш ход!', MSG_WARNING);
      return;
    }

    if (s.moveFrom === null) {
      const piece = s.board[positionNum];
      if (!piece || getPieceColor(piece) !== s.myColor) return;
      selectPiece(positionNum, s);
      return;
    }

    if (s.moveFrom === positionNum) {
      deselectPiece();
      return;
    }

    const targetPiece = s.board[positionNum];
    if (targetPiece && getPieceColor(targetPiece) === s.myColor) {
      selectPiece(positionNum, s);
      return;
    }

    send(buildMovePayload(s, s.moveFrom, positionNum));
    deselectPiece();
  }, [isBlocked, stateRef, showMessage, selectPiece, deselectPiece, send]);
}
