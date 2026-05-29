import { useEffect, useCallback, useRef, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import useWebSocket from './hooks/useWebSocket';
import useGameReducer, { GAME_ACTIONS } from './hooks/useGameReducer';
import useMessage from './hooks/useMessage';
import useEscapeKey from './hooks/useEscapeKey';
import useCellClick from './hooks/useCellClick';
import BoardGrid from './BoardGrid';
import WaitingScreen from './components/WaitingScreen';
import DisconnectOverlay from './components/DisconnectOverlay';
import MoveHistory from './components/MoveHistory';
import { MSG_ERROR, MSG_WARNING, ROOM_AI, ROOM_PUBLIC } from './constants';
import { createRoom } from './api';
import {
  buildDeclineDrawPayload,
  buildOfferDrawPayload,
  buildPassPayload,
  buildRequestRematchPayload,
  buildResignPayload,
  buildCancelGamePayload,
} from './utils/wsPayloads';
import GameControls from './components/GameControls';
import GameResultActions from './components/GameResultActions';
import GameClock from './components/GameClock';
import GameChat from './components/GameChat';
import PlayerBar from './components/PlayerBar';
import { getClientId } from './api';
import { formatGameOverMessage, getBoardSideOrder } from './utils';
import { translateWsErrorMessage } from './i18n/translateServerMessage';

const ROOM_ERROR_TYPES = new Set([
  'room_full',
  'already_in_game',
  'room_not_found',
  'reconnect_failed',
]);

export default function Game() {
  const { t } = useTranslation();
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
      showMessage(translateWsErrorMessage(statusInfo.message), MSG_WARNING);
      return;
    }
    if (statusInfo.type === 'connected') {
      setWsReconnecting(false);
      showMessage(t('game.connectionRestored'));
    }
  }, [showMessage, t]);

  const handleWsError = useCallback((errorInfo) => {
    const error = typeof errorInfo === 'string'
      ? { type: 'unknown', recoverable: false, message: errorInfo }
      : errorInfo;

    if (!error?.message) return;
    const message = translateWsErrorMessage(error.message);

    if (error.recoverable) {
      showMessage(message, MSG_WARNING);
      return;
    }

    if (ROOM_ERROR_TYPES.has(error.type)) {
      setWsReconnecting(false);
      dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: message });
      const delay = error.type === 'reconnect_failed' ? 4000 : 2000;
      setTimeout(() => navigate('/'), delay);
      return;
    }

    if (stateRef.current.waiting) {
      dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: message });
      return;
    }

    showMessage(message, MSG_ERROR);
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
      showMessage(t('game.connectionLost'), MSG_WARNING);
    }
  }, [send, showMessage, t]);

  const acceptDraw = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver) return;
    if (!s.drawOfferFrom || s.drawOfferFrom === s.myColor) return;
    if (!send(buildOfferDrawPayload())) {
      showMessage(t('game.connectionLost'), MSG_WARNING);
    }
  }, [send, showMessage, t]);

  const declineDraw = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver) return;
    if (!s.drawOfferFrom || s.drawOfferFrom === s.myColor) return;
    send(buildDeclineDrawPayload());
  }, [send]);

  const cancelGame = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver || modeAi) return;
    if (s.movesHistory.some((m) => m.mover === s.myColor)) return;
    dispatch({
      type: GAME_ACTIONS.GAME_CANCELLED,
      payload: { message: t('server.cancelYou') },
    });
    if (!send(buildCancelGamePayload())) {
      showMessage(t('game.connectionLost'), MSG_WARNING);
    }
  }, [modeAi, send, showMessage, dispatch, t]);

  const drawPending = state.drawOfferFrom != null && state.drawOfferFrom === state.myColor;
  const drawIncoming = state.drawOfferFrom != null && state.drawOfferFrom !== state.myColor;
  const canCancelGame = !modeAi
    && !state.gameOver
    && !!state.myColor
    && !drawIncoming
    && !state.movesHistory.some((m) => m.mover === state.myColor);

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
      showMessage(e?.message || t('game.createNewFailed'), MSG_ERROR);
    }
  }, [modeAi, navigate, showMessage, t]);

  const sendChat = useCallback((text) => {
    send({ type: 'chat', text });
  }, [send]);

  const requestRematch = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver && !modeAi && !s.rematchReady && !s.rematchUnavailable) {
      send(buildRequestRematchPayload());
    }
  }, [modeAi, send]);

  const opponentLabel = (() => {
    const myId = getClientId();
    const opp = state.playersInfo?.find((p) => p.client_id !== myId);
    if (!opp) return null;
    return opp.is_anonymous ? t('lobby.anonymous') : `@${opp.username}`;
  })();

  if (state.waiting) {
    return (
      <WaitingScreen
        roomId={roomId}
        modeAi={modeAi}
        showInviteLink={showInviteLink}
        joiningError={state.joiningError}
        reconnectMessage={wsReconnecting ? t('game.reconnecting') : ''}
        opponentLabel={opponentLabel}
        onCopyFeedback={(type, text) => showMessage(text, type === 'success' ? 'info' : MSG_ERROR)}
      />
    );
  }

  const resultText = state.gameOver
    ? formatGameOverMessage(state.winner, state.gameOverReason)
    : t('game.draw');

  const { top: boardTop, bottom: boardBottom } = getBoardSideOrder(state.myColor);

  const moveHistoryProps = {
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

  const actionsBarClass = [
    'game-actions-bar',
    state.gameOver ? 'game-actions-bar--game-over' : '',
  ].filter(Boolean).join(' ');

  const renderActionsBar = (slot) => (
    <div className={`${actionsBarClass} game-actions-bar--${slot}`}>
      {state.gameOver ? (
        <>
          <p className="game-result-text game-result-text--bar">{resultText}</p>
          <GameResultActions
            modeAi={modeAi}
            onLobby={goToLobby}
            onPlayAgain={playAgain}
            onRematch={requestRematch}
            rematchReady={state.rematchReady}
            rematchOpponentReady={state.rematchOpponentReady}
            rematchUnavailable={state.rematchUnavailable}
          />
          {!modeAi && state.rematchUnavailable && (
            <p className="game-result-hint game-result-hint--warn game-result-hint--bar">
              {t('result.rematchHint')}
            </p>
          )}
        </>
      ) : (
        <GameControls
          canPass={state.canPass}
          onPass={skipTurn}
          onOfferDraw={offerDraw}
          onAcceptDraw={acceptDraw}
          onDeclineDraw={declineDraw}
          onCancelGame={cancelGame}
          onResign={resign}
          drawPending={drawPending}
          drawIncoming={drawIncoming}
          canCancelGame={canCancelGame}
          hideDraw={modeAi}
        />
      )}
    </div>
  );

  return (
    <div className="game-page">
      <button type="button" className="hud-title" onClick={goToLobby} title={t('game.toLobby')}>
        {t('game.hudTitle')}
      </button>
      <div className="room-layout">
        <section className="game-viewport-first" aria-label={t('game.boardAria')}>
        <div className="game-screen-fit">
          <PlayerBar
            position="top"
            color={boardTop}
            playersInfo={state.playersInfo}
            timer={state.timer}
            moversColor={state.moversColor}
            myColor={state.myColor}
            timeControl={state.timeControl}
            countsByType={state.countsByType}
          />
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

          <PlayerBar
            position="bottom"
            color={boardBottom}
            playersInfo={state.playersInfo}
            timer={state.timer}
            moversColor={state.moversColor}
            myColor={state.myColor}
            timeControl={state.timeControl}
            countsByType={state.countsByType}
          />
        </div>

        {renderActionsBar('viewport')}

        <div className="move-history-slot move-history-slot--viewport">
          <MoveHistory {...moveHistoryProps} />
        </div>
        </section>

        <aside className="room-right">
          <div className="room-side-panel">
            <GameClock
              timer={state.timer}
              moversColor={state.moversColor}
              myColor={state.myColor}
              timeControl={state.timeControl}
              playersInfo={state.playersInfo}
              countsByType={state.countsByType}
              middleSlot={renderActionsBar('sidebar')}
            />

            <div className="move-history-slot move-history-slot--sidebar">
              <MoveHistory {...moveHistoryProps} />
            </div>

            <div className="room-sidebar-extra">
              {message && (
                <div className={`message message-${messageType}`}>{message}</div>
              )}
            </div>
          </div>

          {!modeAi && (
            <aside className="room-left" aria-label={t('game.chatAria')}>
              <GameChat
                messages={state.chatMessages}
                onSend={sendChat}
                disabled={wsReconnecting || state.opponentDisconnected}
              />
            </aside>
          )}
        </aside>
      </div>
    </div>
  );
}
