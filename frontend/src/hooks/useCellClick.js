import { useCallback } from 'react';
import { GAME_ACTIONS } from '../game/actions';
import { MSG_WARNING } from '../constants';
import { getPieceColor } from '../utils';
import { buildHintPayload, buildMovePayload } from '../utils/wsPayloads';
import i18n from '../i18n';

function chainCaptureCell(state) {
  const pos = state.posForMandatoryCapture;
  return pos != null ? Number(pos) : null;
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
    if (!send(buildHintPayload(positionNum))) {
      showMessage(i18n.t('game.connectionLost'), MSG_WARNING);
    }
  }, [dispatch, send, showMessage]);

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
        if (!send(buildHintPayload(chainCell))) {
          showMessage(i18n.t('game.connectionLost'), MSG_WARNING);
        }
        return;
      }

      const targetPiece = s.board[positionNum];
      if (targetPiece && getPieceColor(targetPiece) === s.myColor) {
        return;
      }

      if (!send(buildMovePayload(s, chainCell, positionNum))) {
        showMessage(i18n.t('game.connectionLost'), MSG_WARNING);
      }
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

    if (!send(buildMovePayload(s, s.moveFrom, positionNum))) {
      showMessage(i18n.t('game.connectionLost'), MSG_WARNING);
      return;
    }
    deselectPiece();
  }, [isBlocked, stateRef, showMessage, selectPiece, deselectPiece, send]);
}
