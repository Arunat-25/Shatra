import { useEffect, useCallback, useRef, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import useWebSocket from './hooks/useWebSocket';
import useGameReducer, { GAME_ACTIONS } from './hooks/useGameReducer';
import useMessage from './hooks/useMessage';
import useEscapeKey from './hooks/useEscapeKey';
import useCellClick from './hooks/useCellClick';
import BoardGrid from './BoardGrid';
import WaitingScreen from './components/WaitingScreen';
import DisconnectOverlay from './components/DisconnectOverlay';
import MoveHistory from './components/MoveHistory';
import PieceCounts from './components/PieceCounts';
import { MSG_ERROR, MSG_WARNING, ROOM_AI, ROOM_PUBLIC } from './constants';
import { createRoom } from './api';
import {
  buildDeclineDrawPayload,
  buildOfferDrawPayload,
  buildPassPayload,
  buildRequestRematchPayload,
  buildResignPayload,
} from './utils/wsPayloads';
import GameControls from './components/GameControls';
import GameClock from './components/GameClock';
import { formatGameOverMessage, isWinner } from './utils';

const ROOM_ERROR_TYPES = new Set([
  'room_full',
  'already_in_game',
  'room_not_found',
  'reconnect_failed',
]);

export default function Game() {
  const navigate = useNavigate();
  const { roomId } = useParams();
  const [searchParams] = useSearchParams();
  const modeAi = searchParams.get('mode') === 'ai';
  const showInviteLink = searchParams.get('mode') === 'private';

  const myColorRef = useRef(null);
  const { state, dispatch, handleServerMessage, deselectPiece } = useGameReducer(
    modeAi,
    () => myColorRef.current,
  );
  const { message, messageType, showMessage } = useMessage();
  const [wsReconnecting, setWsReconnecting] = useState(false);
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

  // Disable page scrolling on the game screen (keep inner panel scrolling).
  useEffect(() => {
    document.body.classList.add('in-game');
    const root = document.getElementById('root');
    root?.classList.add('in-game');
    return () => {
      document.body.classList.remove('in-game');
      root?.classList.remove('in-game');
    };
  }, []);

  // When navigating to a different room (e.g. "Play Again"), the component stays mounted.
  // Reset local game state so flags like aiThinking/opponentDisconnected don't leak to the next room.
  useEffect(() => {
    myColorRef.current = null;
    dispatch({ type: GAME_ACTIONS.RESET_GAME });
  }, [roomId, modeAi, dispatch]);

  const handleWsMessage = useCallback((data) => {
    if (data.your_color) {
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
    if (!statusInfo) return;
    if (statusInfo.type === 'reconnecting') {
      setWsReconnecting(true);
      showMessage(statusInfo.message, MSG_WARNING);
      return;
    }
    if (statusInfo.type === 'connected') {
      setWsReconnecting(false);
      showMessage('Соединение восстановлено');
    }
  }, [showMessage]);

  const handleWsError = useCallback((errorInfo) => {
    const error = typeof errorInfo === 'string'
      ? { type: 'unknown', recoverable: false, message: errorInfo }
      : errorInfo;

    if (!error?.message) return;

    if (error.recoverable) {
      showMessage(error.message, MSG_WARNING);
      return;
    }

    if (ROOM_ERROR_TYPES.has(error.type)) {
      setWsReconnecting(false);
      dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: error.message });
      const delay = error.type === 'reconnect_failed' ? 4000 : 2000;
      setTimeout(() => navigate('/'), delay);
      return;
    }

    if (stateRef.current.waiting) {
      dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: error.message });
      return;
    }

    showMessage(error.message, MSG_ERROR);
  }, [navigate, showMessage]);

  const { send } = useWebSocket(roomId, handleWsMessage, handleWsError, handleWsStatus);

  const isBoardBlocked =
    state.gameOver || state.aiThinking || state.opponentDisconnected || wsReconnecting;

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

  const resign = useCallback(() => {
    if (stateRef.current.gameOver) return;
    send(buildResignPayload());
  }, [send]);

  const offerDraw = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver) return;
    if (s.drawOfferFrom === s.myColor) return;
    if (!send(buildOfferDrawPayload())) {
      showMessage('Нет соединения. Дождитесь переподключения…', MSG_WARNING);
    }
  }, [send, showMessage]);

  const acceptDraw = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver) return;
    if (!s.drawOfferFrom || s.drawOfferFrom === s.myColor) return;
    if (!send(buildOfferDrawPayload())) {
      showMessage('Нет соединения. Дождитесь переподключения…', MSG_WARNING);
    }
  }, [send, showMessage]);

  const declineDraw = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver) return;
    if (!s.drawOfferFrom || s.drawOfferFrom === s.myColor) return;
    send(buildDeclineDrawPayload());
  }, [send]);

  const drawPending = state.drawOfferFrom != null && state.drawOfferFrom === state.myColor;
  const drawIncoming = state.drawOfferFrom != null && state.drawOfferFrom !== state.myColor;

  const playAgain = useCallback(async () => {
    try {
      if (modeAi) {
        const data = await createRoom(ROOM_AI, null, null);
        navigate(`/${data.room_id}?mode=ai`, { replace: true });
        return;
      }
      const data = await createRoom(
        ROOM_PUBLIC,
        stateRef.current.timeControl,
        stateRef.current.increment,
      );
      navigate(`/${data.room_id}`, { replace: true });
    } catch (e) {
      showMessage(e?.message || 'Не удалось создать новую игру', MSG_ERROR);
    }
  }, [modeAi, navigate, showMessage]);

  const requestRematch = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver && !modeAi && !s.rematchReady && !s.rematchUnavailable) {
      send(buildRequestRematchPayload());
    }
  }, [modeAi, send]);

  if (state.waiting) {
    return (
      <WaitingScreen
        roomId={roomId}
        modeAi={modeAi}
        showInviteLink={showInviteLink}
        joiningError={state.joiningError}
        reconnectMessage={wsReconnecting ? 'Переподключение…' : ''}
        onCopyFeedback={(type, text) => showMessage(text, type === 'success' ? 'info' : MSG_ERROR)}
      />
    );
  }

  const win = state.gameOver ? isWinner(state.winner, state.myColor) : null;

  let bannerVariant = 'draw';
  if (win === true) bannerVariant = 'win';
  if (win === false) bannerVariant = 'loss';

  const resultText = state.gameOver
    ? formatGameOverMessage(state.winner, state.gameOverReason)
    : 'Ничья';

  return (
    <div className="game-page">
      <button type="button" className="hud-title" onClick={goToLobby} title="В лобби">
        Шатра
      </button>
      <div className="room-layout">
        <div className="room-board">
          <div
            className={[
              'board',
              isBoardBlocked ? 'disabled' : '',
              (state.aiThinking || state.opponentDisconnected) ? 'board-dimmed' : '',
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
        </div>

        <aside className="room-right">
          <GameClock
            timer={state.timer}
            moversColor={state.moversColor}
            myColor={state.myColor}
            timeControl={state.timeControl}
          />
          <PieceCounts countsByType={state.countsByType} />

          <MoveHistory
            movesHistory={state.movesHistory}
            viewingHistoryIndex={state.viewingHistoryIndex}
            onViewMove={(idx) => dispatch({ type: GAME_ACTIONS.VIEW_HISTORY_MOVE, payload: idx })}
            onExitHistory={() => dispatch({ type: GAME_ACTIONS.EXIT_HISTORY })}
            onStepBack={() => dispatch({ type: GAME_ACTIONS.HISTORY_STEP_BACK })}
            onStepForward={() => dispatch({ type: GAME_ACTIONS.HISTORY_STEP_FORWARD })}
            canStepBack={state.movesHistory.length > 0 && (state.viewingHistoryIndex === null ? state.movesHistory.length - 1 > 0 : state.viewingHistoryIndex > 0)}
            canStepForward={state.movesHistory.length > 0 && state.viewingHistoryIndex !== null}
          />

          {state.gameOver && (
            <div className={`game-result-panel game-result-panel--${bannerVariant}`}>
              <div className="game-result-text">{resultText}</div>
              <div className={`game-result-actions ${!modeAi ? 'game-result-actions--stacked' : ''}`}>
                <button type="button" className="game-result-btn game-result-btn--primary" onClick={goToLobby}>
                  В лобби
                </button>
                <button
                  type="button"
                  className="game-result-btn game-result-btn--secondary"
                  onClick={playAgain}
                  title="Создать новую комнату в зале ожидания"
                >
                  Снова
                </button>
                {!modeAi && (
                  <>
                  <p className="game-result-hint">
                    Реванш — та же комната, цвета меняются. Снова — новая игра.
                  </p>
                  <button
                    type="button"
                    className={[
                      'game-result-btn',
                      'game-result-btn--rematch',
                      !state.rematchUnavailable && (state.rematchReady || state.rematchOpponentReady)
                        ? 'game-result-btn--rematch-pulse'
                        : '',
                      state.rematchUnavailable ? 'game-result-btn--rematch-unavailable' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={requestRematch}
                    disabled={state.rematchReady || state.rematchUnavailable}
                    title={
                      state.rematchUnavailable
                        ? 'Соперник вышел'
                        : state.rematchReady
                          ? 'Ожидание соперника'
                          : state.rematchOpponentReady
                            ? 'Соперник ждёт реванша'
                            : 'Реванш'
                    }
                  >
                    Реванш
                  </button>
                  {state.rematchUnavailable && (
                    <p className="game-result-hint game-result-hint--warn">
                      Соперник вышел — нажмите «Снова» для новой игры.
                    </p>
                  )}
                  </>
                )}
              </div>
            </div>
          )}

          {!state.gameOver && (
            <GameControls
              canPass={state.canPass}
              onPass={skipTurn}
              onOfferDraw={offerDraw}
              onAcceptDraw={acceptDraw}
              onDeclineDraw={declineDraw}
              onResign={resign}
              drawPending={drawPending}
              drawIncoming={drawIncoming}
              hideDraw={modeAi}
            />
          )}

          {message && (
            <div className={`message message-${messageType}`}>{message}</div>
          )}

        </aside>
      </div>
    </div>
  );
}
