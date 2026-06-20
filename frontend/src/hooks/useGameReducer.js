import { useCallback, useRef, useEffect, useReducer } from 'react';
import { GAME_ACTIONS } from '../game/actions';
import { gameReducer, initialGameState } from '../game/reducer';
import { dispatchServerMessage } from '../game/messageHandlers';
import { playForAction, playForServerError } from '../audio/playGameSound';
import {
  classifyIncomingPly,
  isMoveConfirmation,
  hasOutstandingPending,
  isOwnOptimisticConfirmation,
  isDuplicateRematchToast,
} from '../game/syncLayer';

export { GAME_ACTIONS } from '../game/actions';

export default function useGameReducer(modeAi, getMyColor) {
  const [state, baseDispatch] = useReducer(gameReducer, initialGameState);
  const stateRef = useRef(state);
  const getMyColorRef = useRef(getMyColor);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  useEffect(() => {
    getMyColorRef.current = getMyColor;
  });

  const readMyColor = useCallback(() => getMyColorRef.current?.(), []);

  const dispatch = useCallback((action) => {
    playForAction(action, stateRef.current, readMyColor);
    baseDispatch(action);
  }, [readMyColor]);

  const handleServerMessage = useCallback(
    (data) => {
      if (data?.status === 'error') {
        playForServerError();
        if (hasOutstandingPending(stateRef.current)) {
          baseDispatch({ type: GAME_ACTIONS.ROLLBACK_OPTIMISTIC });
        }
      }

      if (isMoveConfirmation(data)) {
        const verdict = classifyIncomingPly(stateRef.current.confirmedPly, data.ply);
        if (verdict === 'stale') return null;
        if (verdict === 'gap') {
          baseDispatch({ type: GAME_ACTIONS.SET_SYNC_STATUS, payload: 'desynced' });
          return { needSync: true };
        }
      }

      const result = dispatchServerMessage(data, dispatch, modeAi, readMyColor);
      if (
        result?.text
        && isMoveConfirmation(data)
        && isOwnOptimisticConfirmation(data, stateRef.current, readMyColor())
      ) {
        return null;
      }
      if (result?.text && isDuplicateRematchToast(data, stateRef.current)) {
        return null;
      }
      return result;
    },
    [modeAi, dispatch, readMyColor],
  );

  const deselectPiece = useCallback(() => {
    dispatch({ type: GAME_ACTIONS.DESELECT });
  }, [dispatch]);

  return { state, dispatch, handleServerMessage, deselectPiece };
}
