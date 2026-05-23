import { useRef, useEffect, useCallback } from 'react';
import { getWsUrl } from '../api';

/**
 * Хук для управления WebSocket-соединением.
 * @param {string} roomId - ID комнаты
 * @param {function} onMessage - колбэк для входящих сообщений
 * @param {function} [onError] - колбэк для ошибок подключения
 * @returns {{ send: function, close: function, wsRef: React.MutableRefObject }}
 */
export default function useWebSocket(roomId, onMessage, onError) {
  const wsRef = useRef(null);
  const intentionalCloseRef = useRef(false);
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onErrorRef.current = onError;
  });

  useEffect(() => {
    if (!roomId) return;

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

    ws.onclose = (event) => {
      if (event.code !== 1000 && !intentionalCloseRef.current) {
        const reason = event.reason || 'Соединение разорвано';
        onErrorRef.current?.(reason);
      }
    };

    ws.onerror = () => {
      // Не вызываем onError — дожидаемся onclose с реальной причиной
    };

    return () => {
      intentionalCloseRef.current = true;
      ws.close();
    };
  }, [roomId]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const close = useCallback(() => {
    intentionalCloseRef.current = true;
    wsRef.current?.close();
  }, []);

  return { send, close, wsRef, intentionalCloseRef };
}
