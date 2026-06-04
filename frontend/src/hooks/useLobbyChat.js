import { useCallback, useEffect, useRef, useState } from 'react';
import { getLobbyWsUrl } from '../api';
import { resolveWsErrorMessage } from '../i18n/resolveMessage';
import {
  classifyClose,
  getReconnectDelay,
  parseWsMessage,
  shouldStopReconnecting,
} from '../wsReconnect';

function normalizeChatMessage(data) {
  return {
    client_id: data.client_id ?? data.from_client_id,
    from_client_id: data.from_client_id ?? data.client_id,
    username: data.username,
    text: data.text,
    ts: data.ts,
    is_anonymous: data.is_anonymous,
    display_name: data.display_name,
  };
}

export default function useLobbyChat(enabled = true) {
  const [messages, setMessages] = useState([]);
  const [error, setError] = useState('');
  const [connected, setConnected] = useState(false);

  const wsRef = useRef(null);
  const intentionalCloseRef = useRef(false);
  const reconnectTimerRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const connectRef = useRef(null);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!enabled) return;

    intentionalCloseRef.current = false;
    const ws = new WebSocket(getLobbyWsUrl());
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      setConnected(true);
      setError('');
    };

    ws.onmessage = (event) => {
      const parsed = parseWsMessage(event.data);
      if (!parsed.ok) {
        setError(parsed.error);
        return;
      }
      const data = parsed.data;
      if (data.type === 'chat_history') {
        const list = (data.messages || []).map(normalizeChatMessage);
        setMessages(list);
        return;
      }
      if (data.type === 'chat') {
        setMessages((prev) => [...prev, normalizeChatMessage(data)]);
        return;
      }
      if (data.message_code) {
        setError(resolveWsErrorMessage(data.message_code));
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      if (intentionalCloseRef.current) return;

      const closeInfo = classifyClose(event);
      if (!closeInfo.recoverable) {
        setError(closeInfo.message || 'Ошибка соединения');
        return;
      }

      reconnectAttemptsRef.current += 1;
      if (shouldStopReconnecting(reconnectAttemptsRef.current)) {
        setError('Не удалось восстановить соединение. Обновите страницу.');
        return;
      }

      const delay = getReconnectDelay(reconnectAttemptsRef.current);
      clearReconnectTimer();
      reconnectTimerRef.current = setTimeout(() => {
        connectRef.current?.();
      }, delay);
    };

    ws.onerror = () => {};
  }, [enabled, clearReconnectTimer]);

  useEffect(() => {
    connectRef.current = connect;
    if (!enabled) {
      intentionalCloseRef.current = true;
      clearReconnectTimer();
      wsRef.current?.close();
      return undefined;
    }

    connect();
    return () => {
      intentionalCloseRef.current = true;
      clearReconnectTimer();
      wsRef.current?.close();
    };
  }, [enabled, connect, clearReconnectTimer]);

  const send = useCallback((text) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify({ type: 'chat', text }));
    return true;
  }, []);

  const clearError = useCallback(() => setError(''), []);

  return {
    messages,
    send,
    error,
    connected,
    clearError,
    disabled: !connected,
  };
}
