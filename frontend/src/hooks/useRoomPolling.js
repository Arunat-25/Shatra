import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Хук для polling списка комнат.
 * @param {function} fetchFn — асинхронная функция получения комнат
 * @param {number} interval — интервал опроса в мс
 */
export default function useRoomPolling(fetchFn, interval) {
  const [rooms, setRooms] = useState([]);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const intervalRef = useRef(null);

  const fetchRooms = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await fetchFn();
      setRooms(data.rooms);
      setError('');
    } catch (e) {
      if (e.message !== 'Ошибка подключения') {
        setError(e.message);
      }
    } finally {
      setRefreshing(false);
    }
  }, [fetchFn]);

  const dismissError = useCallback(() => setError(''), []);
  const setExternalError = useCallback((msg) => setError(msg), []);

  useEffect(() => {
    const initialTimer = setTimeout(() => { void fetchRooms(); }, 0);
    intervalRef.current = setInterval(fetchRooms, interval);

    const onVisibilityChange = () => {
      if (document.hidden) {
        clearInterval(intervalRef.current);
      } else {
        fetchRooms();
        intervalRef.current = setInterval(fetchRooms, interval);
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(intervalRef.current);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [fetchRooms, interval]);

  return { rooms, error, refreshing, dismissError, setExternalError, fetchRooms };
}