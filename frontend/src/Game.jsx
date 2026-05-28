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
import { MSG_ERROR, MSG_SUCCESS, MSG_WARNING } from './constants';
import { getClientId } from './api';
import { buildPassPayload } from './utils/wsPayloads';

const ROOM_ERROR_TYPES = new Set(['room_full', 'already_in_game', 'room_not_found']);

export default function Game() {
  const navigate = useNavigate();
  const { roomId } = useParams();
  const [searchParams] = useSearchParams();
  const modeAi = searchParams.get('mode') === 'ai';

  const { state, dispatch, handleServerMessage, deselectPiece } = useGameReducer(modeAi);
  const { message, messageType, showMessage } = useMessage();
  const [connectionStatus, setConnectionStatus] = useState({ type: 'idle', message: '' });
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

  const handleWsStatus = useCallback((statusInfo) => {
    if (!statusInfo) {
      setConnectionStatus({ type: 'idle', message: '' });
      return;
    }

    if (statusInfo.type === 'reconnecting') {
      setConnectionStatus({ type: 'reconnecting', message: statusInfo.message });
      showMessage(statusInfo.message, MSG_WARNING);
      return;
    }

    if (statusInfo.type === 'connected') {
      setConnectionStatus({ type: 'idle', message: '' });
      showMessage('Соединение восстановлено');
    }
  }, [showMessage]);

  const handleWsError = useCallback((errorInfo) => {
    const error = typeof errorInfo === 'string'
      ? { type: 'unknown', recoverable: false, message: errorInfo }
      : errorInfo;

    if (!error?.message) {
      return;
    }

    if (error.recoverable) {
      showMessage(error.message, MSG_WARNING);
      return;
    }

    if (ROOM_ERROR_TYPES.has(error.type)) {
      dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: error.message });
      setTimeout(() => navigate('/'), 2000);
      return;
    }

    if (state.waiting) {
      dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: error.message });
      return;
    }

    showMessage(error.message, MSG_ERROR);
  }, [navigate, showMessage, state.waiting]);

  const { send } = useWebSocket(roomId, handleWsMessage, handleWsError, handleWsStatus);

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
        reconnectMessage={connectionStatus.type === 'reconnecting' ? connectionStatus.message : ''}
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
            myColor={state.myColor}
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
