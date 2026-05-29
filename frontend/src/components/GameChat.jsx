import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getClientId } from '../api';

function formatAuthor(msg) {
  if (msg.display_name) return msg.display_name;
  if (!msg.is_anonymous && msg.username) return `@${msg.username}`;
  return null;
}

export default function GameChat({ messages, onSend, disabled }) {
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const listRef = useRef(null);
  const myId = getClientId();

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const submit = useCallback((e) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  }, [text, disabled, onSend]);

  return (
    <div className="game-chat">
      <div className="game-chat-header">{t('chat.title')}</div>
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
    </div>
  );
}
