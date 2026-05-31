import { useTranslation } from 'react-i18next';
import GameClock from '../GameClock';
import GameChat from '../GameChat';
import MoveHistory from '../MoveHistory';
import OpponentDisconnectStatus from './OpponentDisconnectStatus';

export default function GameDesktopLayout({
  state,
  modeAi,
  wsReconnecting,
  message,
  messageType,
  actionsBar,
  moveHistoryProps,
  onSendChat,
  chatHidden,
  onToggleChatHidden,
  roomId,
}) {
  const { t } = useTranslation();

  return (
    <aside className="room-right">
      <div className="room-side-panel">
        <GameClock
          timer={state.timer}
          moversColor={state.moversColor}
          myColor={state.myColor}
          timeControl={state.timeControl}
          playersInfo={state.playersInfo}
          countsByType={state.countsByType}
          middleSlot={actionsBar}
        />

        <div className="move-history-slot move-history-slot--sidebar">
          <MoveHistory {...moveHistoryProps} />
        </div>

        <div className="room-sidebar-extra">
          {state.opponentDisconnected && (
            <OpponentDisconnectStatus
              placement="sidebar"
              disconnectCountdown={state.disconnectCountdown}
            />
          )}
          {message && (
            <div className={`message message-${messageType}`}>{message}</div>
          )}
        </div>
      </div>

      {!modeAi && (
        <aside className="room-left" aria-label={t('game.chatAria')}>
          <GameChat
            messages={state.chatMessages}
            onSend={onSendChat}
            disabled={wsReconnecting || state.opponentDisconnected}
            chatHidden={chatHidden}
            onToggleHidden={onToggleChatHidden}
            roomId={roomId}
          />
        </aside>
      )}
    </aside>
  );
}
