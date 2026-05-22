import { useRef, useEffect, useCallback } from 'react';
import { getWsUrl } from '../utils';

/**
 * Хук для управления WebSocket-соединением.
 * @param {string} roomId - ID комнаты
 * @param {number|null} playerId - ID игрока
 * @param {function} onMessage - колбэк для входящих сообщений
 * @param {function} [onError] - колбэк для ошибок подключения
 * @returns {{ send: function, close: function, wsRef: React.MutableRefObject }}
 */
export default function useWebSocket(roomId, playerId, onMessage, onError) {
  const wsRef = useRef(null);
  const intentionalCloseRef = useRef(false);

  useEffect(() => {
    if (!roomId) return;

    intentionalCloseRef.current = false;
    const url = getWsUrl(roomId, playerId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage?.(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = (event) => {
      if (event.code !== 1000 && !intentionalCloseRef.current) {
        onError?.('Соединение разорвано');
      }
    };

    ws.onerror = () => {
      onError?.('Ошибка подключения');
    };

    return () => {
      intentionalCloseRef.current = true;
      ws.close();
    };
  }, [roomId, playerId, onMessage, onError]);

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