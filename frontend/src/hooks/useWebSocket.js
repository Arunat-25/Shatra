import { useEffect, useRef, useCallback } from 'react';
import { getWsUrl } from '../api';

const RECONNECT_BASE_DELAY_MS = 500;
const RECONNECT_MAX_DELAY_MS = 5000;

const FATAL_CLOSE_REASONS = ['комната уже заполнена', 'комната не найдена', 'вы уже в игре'];

function getReconnectDelay(attempt) {
  const delay = RECONNECT_BASE_DELAY_MS * 2 ** (attempt - 1);
  return Math.min(delay, RECONNECT_MAX_DELAY_MS);
}

function classifyClose(event) {
  const reason = (event.reason || '').toLowerCase();

  if (event.code === 1000) {
    return { recoverable: false, type: 'normal' };
  }

  if (FATAL_CLOSE_REASONS.some((item) => reason.includes(item))) {
    return {
      recoverable: false,
      type: 'fatal',
      message: event.reason || 'Не удалось подключиться к комнате',
    };
  }

  return {
    recoverable: true,
    type: 'transient',
    message: event.reason || 'Потеряно соединение. Пытаюсь восстановить...',
  };
}

export default function useWebSocket(roomId, onMessage, onError, onStatus) {
  const wsRef = useRef(null);
  const intentionalCloseRef = useRef(false);
  const reconnectTimerRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectWarningShownRef = useRef(false);
  const connectRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);
  const onStatusRef = useRef(onStatus);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onErrorRef.current = onError;
    onStatusRef.current = onStatus;
  }, [onMessage, onError, onStatus]);

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!roomId) {
      return;
    }

    intentionalCloseRef.current = false;
    const url = getWsUrl(roomId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessageRef.current?.(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      reconnectWarningShownRef.current = false;
      clearReconnectTimer();
      onStatusRef.current?.({ type: 'connected' });
    };

    ws.onclose = (event) => {
      if (intentionalCloseRef.current) {
        return;
      }

      const closeInfo = classifyClose(event);

      if (!closeInfo.recoverable) {
        onErrorRef.current?.({
          type: closeInfo.type,
          recoverable: false,
          message: closeInfo.message || 'Ошибка соединения',
        });
        return;
      }

      reconnectAttemptsRef.current += 1;
      if (!reconnectWarningShownRef.current) {
        reconnectWarningShownRef.current = true;
        onStatusRef.current?.({ type: 'reconnecting', message: closeInfo.message });
      }

      const nextDelay = getReconnectDelay(reconnectAttemptsRef.current);
      clearReconnectTimer();
      reconnectTimerRef.current = setTimeout(() => {
        connectRef.current?.();
      }, nextDelay);
    };

    ws.onerror = () => {
      // Ошибка будет обработана в onclose.
    };
  }, [clearReconnectTimer, roomId]);

  useEffect(() => {
    connectRef.current = connect;
    connect();

    return () => {
      intentionalCloseRef.current = true;
      clearReconnectTimer();
      wsRef.current?.close();
    };
  }, [connect, clearReconnectTimer]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const close = useCallback(() => {
    intentionalCloseRef.current = true;
    clearReconnectTimer();
    wsRef.current?.close();
  }, [clearReconnectTimer]);

  return { send, close, wsRef, intentionalCloseRef };
}
