import { useEffect, useCallback, useRef } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import useGameReducer, { GAME_ACTIONS } from './hooks/useGameReducer';
import { buildMoveHistoryProps } from './game/moveHistoryProps';
import useGameWebSocket from './hooks/useGameWebSocket';
import useGameActions from './hooks/useGameActions';
import useMessage from './hooks/useMessage';
import useEscapeKey from './hooks/useEscapeKey';
import useCellClick from './hooks/useCellClick';
import WaitingScreen from './components/WaitingScreen';
import GameActionsBar from './components/game/GameActionsBar';
import GameViewport from './components/game/GameViewport';
import GameDesktopLayout from './components/game/GameDesktopLayout';
import LocaleSwitcher from './components/LocaleSwitcher';
import { MSG_ERROR } from './constants';
import { getClientId } from './api';
import { formatGameOverMessage, getBoardSideOrder } from './utils';

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

  const { send, wsReconnecting, stateRef } = useGameWebSocket(
    roomId,
    modeAi,
    { myColorRef, state, dispatch, handleServerMessage, showMessage, navigate },
  );

  const actions = useGameActions({
    send,
    showMessage,
    modeAi,
    navigate,
    dispatch,
    stateRef,
    state,
  });

  useEffect(() => {
    document.body.classList.add('in-game');
    const root = document.getElementById('root');
    root?.classList.add('in-game');
    return () => {
      document.body.classList.remove('in-game');
      root?.classList.remove('in-game');
    };
  }, []);

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
    ? formatGameOverMessage(
      state.winnerColor,
      state.gameOverReason,
      state.gameOverMessageCode,
    )
    : t('game.draw');

  const { top: boardTop, bottom: boardBottom } = getBoardSideOrder(state.myColor);
  const moveHistoryProps = buildMoveHistoryProps(state, dispatch);

  const actionsBarProps = { state, modeAi, resultText, actions };
  const viewportActions = <GameActionsBar slot="viewport" {...actionsBarProps} />;
  const sidebarActions = <GameActionsBar slot="sidebar" {...actionsBarProps} />;

  return (
    <div className="game-page">
      <header className="game-hud">
        <button
          type="button"
          className="hud-title"
          onClick={actions.goToLobby}
          title={t('game.toLobby')}
        >
          {t('game.hudTitle')}
        </button>
        <LocaleSwitcher compact />
      </header>
      <div className="room-layout">
        <GameViewport
          boardTop={boardTop}
          boardBottom={boardBottom}
          state={state}
          isBoardBlocked={isBoardBlocked}
          onCellClick={handleCellClickWrapped}
          actionsBar={viewportActions}
          moveHistoryProps={moveHistoryProps}
        />
        <GameDesktopLayout
          state={state}
          modeAi={modeAi}
          wsReconnecting={wsReconnecting}
          message={message}
          messageType={messageType}
          actionsBar={sidebarActions}
          moveHistoryProps={moveHistoryProps}
          onSendChat={actions.sendChat}
        />
      </div>
    </div>
  );
}
