import { useTranslation } from 'react-i18next';
import GameChat from '../GameChat';

export default function GameMobilePanel({
  state,
  modeAi,
  wsReconnecting,
  message,
  messageType,
  onSendChat,
  chatHidden,
  onToggleChatHidden,
  roomId,
}) {
  const { t } = useTranslation();

  if (modeAi) {
    return message ? (
      <div className="game-mobile-panel">
        <div className={`message message-${messageType}`}>{message}</div>
      </div>
    ) : null;
  }

  return (
    <div className="game-mobile-panel">
      {message && (
        <div className={`message message-${messageType}`}>{message}</div>
      )}
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
    </div>
  );
}
