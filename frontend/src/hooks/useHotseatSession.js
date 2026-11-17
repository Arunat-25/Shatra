import { useCallback, useEffect, useRef, useState } from 'react';
import { GAME_ACTIONS } from './useGameReducer';
import { createHotseatReferee } from '../game/hotseatReferee';

/**
 * Хотсит: локальная сессия партии двух игроков на одном устройстве.
 *
 * Реализует тот же интерфейс, что useGameWebSocket (send/wsReconnecting/
 * stateRef/setBoardRef), поэтому Game.jsx не отличает её от онлайн-сессии.
 * Все «серверные» сообщения генерирует локальный рефери (hotseatReferee).
 */
export default function useHotseatSession({
  enabled = false,
  myColorRef,
  state,
  dispatch,
  handleServerMessage,
  showMessage,
}) {
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const refereeRef = useRef(null);
  if (refereeRef.current === null) {
    refereeRef.current = createHotseatReferee();
  }

  const [wsReconnecting] = useState(false);

  const boardRef = useRef({});
  const setBoardRef = useCallback((board) => {
    boardRef.current = board || {};
  }, []);

  const consume = useCallback(
    (message) => {
      // Доска хотсита всегда развёрнута к текущему игроку.
      const nextColor = message?.your_color ?? message?.movers_color;
      if (nextColor === 'белый' || nextColor === 'черный') {
        myColorRef.current = nextColor;
        dispatch({ type: GAME_ACTIONS.SET_MY_COLOR, payload: nextColor });
      }
      const result = handleServerMessage(message);
      if (result?.text) showMessage(result.text, result.type);
    },
    [dispatch, handleServerMessage, myColorRef, showMessage],
  );

  useEffect(() => {
    if (!enabled) return undefined;
    consume(refereeRef.current.start());
    return undefined;
    // Партия стартует один раз при входе в режим хотсита.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  const send = useCallback(
    (payload) => {
      if (!enabled) return false;
      const messages = refereeRef.current.handleSend(payload);
      for (const message of messages) consume(message);
      return true;
    },
    [enabled, consume],
  );

  return { send, wsReconnecting, stateRef, setBoardRef };
}
