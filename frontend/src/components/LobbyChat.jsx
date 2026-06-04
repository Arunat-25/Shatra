import React from 'react';
import { useTranslation } from 'react-i18next';
import ChatPanel from './ChatPanel';
import useLobbyChat from '../hooks/useLobbyChat';

export default function LobbyChat() {
  const { t } = useTranslation();
  const { messages, send, error, disabled, clearError } = useLobbyChat(true);

  return (
    <div className="lobby-chat">
      {error && (
        <div className="lobby-chat-error" role="alert">
          <p>{error}</p>
          <button type="button" className="error-dismiss" onClick={clearError} aria-label={t('lobby.closeError')}>
            ✕
          </button>
        </div>
      )}
      <ChatPanel
        className="game-chat lobby-chat-panel"
        messages={messages}
        onSend={send}
        disabled={disabled}
        maxLength={500}
        title={t('lobbyChat.title')}
        emptyText={t('lobbyChat.empty')}
        placeholder={t('lobbyChat.placeholder')}
        sendLabel={t('lobbyChat.send')}
      />
      <p className="lobby-chat-hint">{t('lobbyChat.cooldownHint')}</p>
    </div>
  );
}
