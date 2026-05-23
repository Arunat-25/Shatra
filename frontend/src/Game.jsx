import { useEffect, useCallback, useRef, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import useWebSocket from './hooks/useWebSocket';
import useGameReducer, { GAME_ACTIONS } from './hooks/useGameReducer';
import useMessage from './hooks/useMessage';
import useEscapeKey from './hooks/useEscapeKey';
import useCellClick from './hooks/useCellClick';
import BoardGrid from './BoardGrid';
import GameHeader from './components/GameHeader';
import GameInfo from './components/GameInfo';
import WaitingScreen from './components/WaitingScreen';
import GameOverScreen from './components/GameOverScreen';
import DisconnectOverlay from './components/DisconnectOverlay';
import MoveHistory from './components/MoveHistory';
import { MSG_SUCCESS } from './constants';
import { getClientId } from './api';
import { buildPassPayload } from './utils/wsPayloads';

export default function Game() {
  const navigate = useNavigate();
  const { roomId } = useParams();
  const [searchParams] = useSearchParams();
  const modeAi = searchParams.get('mode') === 'ai';

  const { state, dispatch, handleServerMessage, deselectPiece } = useGameReducer(modeAi);
  const { message, messageType, showMessage } = useMessage();
  const myColorRef = useRef(null);
  const stateRef = useRef(state);
  const handleServerMessageRef = useRef(handleServerMessage);
  const showMessageRef = useRef(showMessage);
  const dispatchRef = useRef(dispatch);

  useEffect(() => {
    stateRef.current = state;
    handleServerMessageRef.current = handleServerMessage;
    showMessageRef.current = showMessage;
    dispatchRef.current = dispatch;
  });

  useEffect(() => {
    if (!state.opponentDisconnected || state.disconnectCountdown <= 0) return;
    const timer = setInterval(() => {
      dispatch({ type: GAME_ACTIONS.DISCONNECT_TICK });
    }, 1000);
    return () => clearInterval(timer);
  }, [state.opponentDisconnected, state.disconnectCountdown, dispatch]);

  const handleWsMessage = useCallback((data) => {
    if (data.your_color && !myColorRef.current) {
      myColorRef.current = data.your_color;
      dispatchRef.current({
        type: GAME_ACTIONS.SET_MY_COLOR,
        payload: data.your_color === 'белый' ? 'белый' : 'черный',
      });
    }
    const msg = handleServerMessageRef.current(data);
    if (msg) showMessageRef.current(msg.text, msg.type);
  }, []);

  const handleWsError = useCallback((errMsg) => {
    dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: errMsg });
    if (errMsg.includes('заполнена') || errMsg.includes('уже в игре')) {
      setTimeout(() => navigate('/'), 2000);
    }
  }, [navigate]);

  const { send } = useWebSocket(roomId, handleWsMessage, handleWsError);

  const isBoardBlocked =
    state.gameOver || state.aiThinking || state.opponentDisconnected;

  const handleCellClick = useCellClick({
    stateRef,
    dispatch,
    send,
    deselectPiece,
    showMessage,
    isBlocked: isBoardBlocked,
  });

  const handleCellClickWrapped = useCallback((positionNum) => {
    if (state.viewingHistoryIndex !== null) return;
    handleCellClick(positionNum);
  }, [state.viewingHistoryIndex, handleCellClick]);

  useEscapeKey(state.moveFrom !== null, deselectPiece);
  useEscapeKey(state.viewingHistoryIndex !== null, () => {
    dispatch({ type: GAME_ACTIONS.EXIT_HISTORY });
  });

  const goToLobby = useCallback(() => navigate('/'), [navigate]);

  const skipTurn = useCallback(() => {
    send(buildPassPayload(stateRef.current));
    dispatch({ type: GAME_ACTIONS.CLEAR_CAN_PASS });
  }, [send, dispatch]);

  const gameOverSessionKey = state.gameOver
    ? `${roomId}-${state.movesHistory.length}-${state.winner}`
    : null;
  const [dismissedGameOverKey, setDismissedGameOverKey] = useState(null);
  const showGameOverScreen = gameOverSessionKey && dismissedGameOverKey !== gameOverSessionKey;

  if (state.waiting) {
    return (
      <WaitingScreen
        roomId={roomId}
        modeAi={modeAi}
        joiningError={state.joiningError}
      />
    );
  }

  return (
    <div className="game-page">
      <div className="game-screen">
        <GameHeader
          myColor={state.myColor}
          moversColor={state.moversColor}
          aiThinking={state.aiThinking}
          modeAi={modeAi}
          onGoToLobby={goToLobby}
          timer={state.timer}
          timeControl={state.timeControl}
          playerId={getClientId()}
        />

        <div
          className={[
            'board',
            isBoardBlocked ? 'disabled' : '',
            state.aiThinking ? 'board-ai-thinking' : '',
          ].filter(Boolean).join(' ')}
        >
          {state.opponentDisconnected && (
            <DisconnectOverlay disconnectCountdown={state.disconnectCountdown} />
          )}
          <BoardGrid
            board={state.board}
            onCellClick={handleCellClickWrapped}
            moveFrom={state.moveFrom}
            highlightedEssential={state.highlightedEssential}
            highlightedCaptured={state.highlightedCaptured}
            lastMove={state.lastMove}
            historyFrom={state.historyFrom}
            historyTo={state.historyTo}
          />
        </div>

        {message && (
          <div className={`message message-${messageType}`}>{message}</div>
        )}

        <GameInfo
          whiteCount={state.whiteCount}
          blackCount={state.blackCount}
          roomId={roomId}
          modeAi={modeAi}
          canPass={state.canPass}
          gameOver={state.gameOver}
          onSkipTurn={skipTurn}
          onCopyLink={() => showMessage('Ссылка скопирована!', MSG_SUCCESS)}
        />
      </div>

      <MoveHistory
        movesHistory={state.movesHistory}
        viewingHistoryIndex={state.viewingHistoryIndex}
        onViewMove={(idx) => dispatch({ type: GAME_ACTIONS.VIEW_HISTORY_MOVE, payload: idx })}
        onExitHistory={() => dispatch({ type: GAME_ACTIONS.EXIT_HISTORY })}
      />

      {showGameOverScreen && (
        <GameOverScreen
          winner={state.winner}
          myColor={state.myColor}
          modeAi={modeAi}
          reason={state.gameOverReason}
          onGoToLobby={() => navigate('/', { replace: true })}
          onViewHistory={() => setDismissedGameOverKey(gameOverSessionKey)}
        />
      )}
    </div>
  );
}
