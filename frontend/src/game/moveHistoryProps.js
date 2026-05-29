import { GAME_ACTIONS } from '../hooks/useGameReducer';

export function buildMoveHistoryProps(state, dispatch) {
  return {
    movesHistory: state.movesHistory,
    viewingHistoryIndex: state.viewingHistoryIndex,
    onViewMove: (idx) => dispatch({ type: GAME_ACTIONS.VIEW_HISTORY_MOVE, payload: idx }),
    onExitHistory: () => dispatch({ type: GAME_ACTIONS.EXIT_HISTORY }),
    onStepBack: () => dispatch({ type: GAME_ACTIONS.HISTORY_STEP_BACK }),
    onStepForward: () => dispatch({ type: GAME_ACTIONS.HISTORY_STEP_FORWARD }),
    canStepBack:
      state.movesHistory.length > 0
      && (state.viewingHistoryIndex === null
        ? state.movesHistory.length - 1 > 0
        : state.viewingHistoryIndex > 0),
    canStepForward: state.movesHistory.length > 0 && state.viewingHistoryIndex !== null,
  };
}
