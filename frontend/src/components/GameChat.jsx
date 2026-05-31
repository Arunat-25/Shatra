import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getClientId } from '../api';

function formatAuthor(msg) {
  if (msg.display_name) return msg.display_name;
  if (!msg.is_anonymous && msg.username) return `@${msg.username}`;
  return null;
}

export default function GameChat({
  messages,
  onSend,
  disabled,
  chatHidden,
  onToggleHidden,
  roomId,
}) {
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const listRef = useRef(null);
  const myId = getClientId();

  useEffect(() => {
    if (listRef.current && !chatHidden) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, chatHidden]);

  const submit = useCallback((e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  }, [text, disabled, onSend]);

  return (
    <div className={`game-chat ${chatHidden ? 'game-chat--hidden' : ''}`}>
      <div className="game-chat-header">
        <span>{t('chat.title')}</span>
        <button
          type="button"
          className="game-chat-toggle"
          onClick={() => {
            onToggleHidden?.();
            if (roomId) {
              sessionStorage.setItem(`chatHidden:${roomId}`, chatHidden ? '0' : '1');
            }
          }}
          aria-pressed={chatHidden}
        >
          {chatHidden ? t('chat.show') : t('chat.hide')}
        </button>
      </div>
      {chatHidden ? (
        <p className="game-chat-hidden-hint">{t('chat.hiddenHint')}</p>
      ) : (
        <div className="game-chat-panel">
          <ul className="game-chat-messages" ref={listRef}>
            {messages.length === 0 && (
              <li className="game-chat-empty">{t('chat.empty')}</li>
            )}
            {messages.map((msg, i) => {
              const author = formatAuthor(msg) || t('chat.anonymous');
              const mine = msg.client_id === myId;
              return (
                <li
                  key={`${msg.ts}-${i}`}
                  className={`game-chat-msg ${mine ? 'game-chat-msg--mine' : ''}`}
                >
                  <span className="game-chat-author">{author}</span>
                  <span className="game-chat-text">{msg.text}</span>
                </li>
              );
            })}
          </ul>
        </div>
      )}
      <form className="game-chat-form" onSubmit={submit}>
        <input
          type="text"
          maxLength={200}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={t('chat.placeholder')}
          disabled={disabled}
          aria-label={t('chat.placeholder')}
        />
        <button type="submit" disabled={disabled || !text.trim()}>
          {t('chat.send')}
        </button>
      </form>
    </div>
  );
}
