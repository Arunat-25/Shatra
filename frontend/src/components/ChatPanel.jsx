import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getClientId } from '../api';

function formatAuthor(msg, anonymousLabel) {
  if (msg.display_name) return msg.display_name;
  if (!msg.is_anonymous && msg.username) return `@${msg.username}`;
  return null;
}

export default function ChatPanel({
  messages,
  onSend,
  disabled,
  maxLength = 200,
  title,
  emptyText,
  placeholder,
  sendLabel,
  className = 'game-chat',
  showToggle = false,
  chatHidden = false,
  onToggleHidden,
  roomId,
}) {
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const listRef = useRef(null);
  const myId = getClientId();

  const resolvedTitle = title ?? t('chat.title');
  const resolvedEmpty = emptyText ?? t('chat.empty');
  const resolvedPlaceholder = placeholder ?? t('chat.placeholder');
  const resolvedSend = sendLabel ?? t('chat.send');
  const anonymousLabel = t('chat.anonymous');

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
    <div className={`${className} ${chatHidden ? 'game-chat--hidden' : ''}`}>
      <div className="game-chat-header">
        <span>{resolvedTitle}</span>
        {showToggle && (
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
        )}
      </div>
      {showToggle && chatHidden ? (
        <p className="game-chat-hidden-hint">{t('chat.hiddenHint')}</p>
      ) : (
        <div className="game-chat-panel">
          <ul className="game-chat-messages" ref={listRef}>
            {messages.length === 0 && (
              <li className="game-chat-empty">{resolvedEmpty}</li>
            )}
            {messages.map((msg, i) => {
              const author = formatAuthor(msg, anonymousLabel) || anonymousLabel;
              const mine = msg.client_id === myId || msg.from_client_id === myId;
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
          maxLength={maxLength}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={resolvedPlaceholder}
          disabled={disabled}
          aria-label={resolvedPlaceholder}
        />
        <button type="submit" disabled={disabled || !text.trim()}>
          {resolvedSend}
        </button>
      </form>
    </div>
  );
}
