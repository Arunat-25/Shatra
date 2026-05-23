import { useReducer, useCallback } from 'react';
import { GAME_ACTIONS } from '../game/actions';
import { gameReducer, initialGameState } from '../game/reducer';
import { dispatchServerMessage } from '../game/messageHandlers';

export { GAME_ACTIONS } from '../game/actions';

export default function useGameReducer(modeAi) {
  const [state, dispatch] = useReducer(gameReducer, initialGameState);

  const handleServerMessage = useCallback(
    (data) => dispatchServerMessage(data, dispatch, modeAi),
    [modeAi],
  );

  const deselectPiece = useCallback(() => {
    dispatch({ type: GAME_ACTIONS.DESELECT });
  }, []);

  return { state, dispatch, handleServerMessage, deselectPiece };
}
