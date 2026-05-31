import { useReducer, useCallback, useRef, useEffect } from 'react';
import { GAME_ACTIONS } from '../game/actions';
import { gameReducer, initialGameState } from '../game/reducer';
import { dispatchServerMessage } from '../game/messageHandlers';
import { playForAction, playForServerError } from '../audio/playGameSound';

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
      }
      return dispatchServerMessage(data, dispatch, modeAi, readMyColor);
    },
    [modeAi, dispatch, readMyColor],
  );

  const deselectPiece = useCallback(() => {
    dispatch({ type: GAME_ACTIONS.DESELECT });
  }, [dispatch]);

  return { state, dispatch, handleServerMessage, deselectPiece };
}
