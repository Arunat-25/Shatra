import { useEffect, useRef, useCallback } from 'react';
import { getWsUrl } from '../api';
import {
  classifyClose,
  getReconnectDelay,
  parseWsMessage,
  shouldStopReconnecting,
} from '../wsReconnect';

export default function useWebSocket(roomId, onMessage, onError, onStatus) {
  const wsRef = useRef(null);
  const intentionalCloseRef = useRef(false);
  const reconnectTimerRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectWarningShownRef = useRef(false);
  const outboundQueueRef = useRef([]);
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

  const flushOutboundQueue = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    while (outboundQueueRef.current.length > 0) {
      ws.send(outboundQueueRef.current.shift());
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
      const parsed = parseWsMessage(event.data);
      if (!parsed.ok) {
        onErrorRef.current?.(parsed.error);
        return;
      }
      onMessageRef.current?.(parsed.data);
    };

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      reconnectWarningShownRef.current = false;
      clearReconnectTimer();
      flushOutboundQueue();
      onStatusRef.current?.({ type: 'connected' });
    };

    ws.onclose = (event) => {
      if (intentionalCloseRef.current) {
        return;
      }

      const closeInfo = classifyClose(event);

      if (!closeInfo.recoverable) {
        outboundQueueRef.current = [];
        onErrorRef.current?.({
          type: closeInfo.type,
          recoverable: false,
          message: closeInfo.message || 'Ошибка соединения',
        });
        return;
      }

      reconnectAttemptsRef.current += 1;

      if (shouldStopReconnecting(reconnectAttemptsRef.current)) {
        outboundQueueRef.current = [];
        onErrorRef.current?.({
          type: 'reconnect_failed',
          recoverable: false,
          message: 'Не удалось восстановить соединение. Обновите страницу или вернитесь в лобби.',
        });
        return;
      }

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
  }, [clearReconnectTimer, flushOutboundQueue, roomId]);

  useEffect(() => {
    connectRef.current = connect;
    reconnectAttemptsRef.current = 0;
    outboundQueueRef.current = [];
    connect();

    return () => {
      intentionalCloseRef.current = true;
      clearReconnectTimer();
      outboundQueueRef.current = [];
      wsRef.current?.close();
    };
  }, [connect, clearReconnectTimer]);

  const send = useCallback((data) => {
    const payload = JSON.stringify(data);
    const ws = wsRef.current;
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(payload);
      return true;
    }
    if (ws?.readyState === WebSocket.CONNECTING) {
      outboundQueueRef.current.push(payload);
      return true;
    }
    return false;
  }, []);

  const retryConnect = useCallback(() => {
    clearReconnectTimer();
    reconnectAttemptsRef.current = 0;
    reconnectWarningShownRef.current = false;
    intentionalCloseRef.current = false;
    wsRef.current?.close();
    connect();
  }, [clearReconnectTimer, connect]);

  const close = useCallback(() => {
    intentionalCloseRef.current = true;
    clearReconnectTimer();
    outboundQueueRef.current = [];
    wsRef.current?.close();
  }, [clearReconnectTimer]);

  return { send, close, retryConnect, wsRef, intentionalCloseRef };
}
