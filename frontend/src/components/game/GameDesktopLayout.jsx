import { useTranslation } from 'react-i18next';
import GameClock from '../GameClock';
import GameChat from '../GameChat';
import MoveHistory from '../MoveHistory';

export default function GameDesktopLayout({
  state,
  modeAi,
  wsReconnecting,
  message,
  messageType,
  actionsBar,
  moveHistoryProps,
  onSendChat,
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
          />
        </aside>
      )}
    </aside>
  );
}
