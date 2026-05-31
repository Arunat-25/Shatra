import { useState, useEffect, useCallback, useRef } from 'react';
import i18n from '../i18n';
import { leaveLobbyPresence } from '../api';

/**
 * Хук для polling списка комнат.
 * @param {function} fetchFn — асинхронная функция получения комнат
 * @param {number} interval — интервал опроса в мс
 */
export default function useRoomPolling(fetchFn, interval) {
  const [rooms, setRooms] = useState([]);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [refreshing, setRefreshing] = useState(false);
  const intervalRef = useRef(null);

  const fetchRooms = useCallback(async () => {
    setRefreshing(true);
    try {
      const data = await fetchFn();
      setRooms(data.rooms);
      setStats(data.stats ?? null);
      setError('');
    } catch (e) {
      if (e.message !== i18n.t('errors.serverUnavailable')) {
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

    const onPageLeave = () => leaveLobbyPresence();

    const onVisibilityChange = () => {
      if (document.hidden) {
        clearInterval(intervalRef.current);
        onPageLeave();
      } else {
        fetchRooms();
        intervalRef.current = setInterval(fetchRooms, interval);
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    window.addEventListener('pagehide', onPageLeave);

    return () => {
      clearTimeout(initialTimer);
      clearInterval(intervalRef.current);
      document.removeEventListener('visibilitychange', onVisibilityChange);
      window.removeEventListener('pagehide', onPageLeave);
      onPageLeave();
    };
  }, [fetchRooms, interval]);

  return { rooms, stats, error, refreshing, dismissError, setExternalError, fetchRooms };
}