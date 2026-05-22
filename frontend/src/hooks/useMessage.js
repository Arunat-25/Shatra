import { useState, useCallback, useRef, useEffect } from 'react';
import { MSG_INFO, MSG_ERROR, MSG_VICTORY, MESSAGE_DURATION } from '../constants';

/**
 * Хук для управления всплывающими сообщениями с авто-скрытием.
 */
export default function useMessage() {
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const showMessage = useCallback((text, type = MSG_INFO) => {
    setMessage(text);
    setMessageType(type);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (type !== MSG_ERROR && type !== MSG_VICTORY) {
      timerRef.current = setTimeout(() => setMessage(''), MESSAGE_DURATION);
    }
  }, []);

  return { message, messageType, showMessage };
}