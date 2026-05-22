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

  useEffect(() => {
    fetchRooms();
    const id = setInterval(fetchRooms, interval);
    const onVisibilityChange = () => {
      if (document.hidden) {
        clearInterval(id);
      } else {
        fetchRooms();
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => {
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [fetchRooms, interval]);

  return { rooms, error, refreshing, setError, fetchRooms };
}