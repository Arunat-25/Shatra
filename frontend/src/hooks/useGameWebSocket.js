import { useEffect, useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import useWebSocket from './useWebSocket';
import { GAME_ACTIONS } from './useGameReducer';
import { MSG_ERROR, MSG_WARNING } from '../constants';
import { resolveWsErrorMessage } from '../i18n/resolveMessage';
import { trackGameEvent } from '../observability/events';
import { buildV2SyncPayload } from '../ws/v2/payloads';

const ROOM_ERROR_TYPES = new Set([
  'room_full',
  'already_in_game',
  'room_not_found',
  'reconnect_failed',
]);

export default function useGameWebSocket(roomId, modeAi, {
  myColorRef,
  state,
  dispatch,
  handleServerMessage,
  showMessage,
  navigate,
}) {
  const { t } = useTranslation();
  const [wsReconnecting, setWsReconnecting] = useState(false);
  const stateRef = useRef(state);
  const handleServerMessageRef = useRef(handleServerMessage);
  const showMessageRef = useRef(showMessage);
  const dispatchRef = useRef(dispatch);

  useEffect(() => {
    stateRef.current = state;
    handleServerMessageRef.current = handleServerMessage;
    showMessageRef.current = showMessage;
    dispatchRef.current = dispatch;
  });

  const joinedRef = useRef(false);
  const sendRef = useRef(() => false);

  useEffect(() => {
    myColorRef.current = null;
    dispatch({ type: GAME_ACTIONS.RESET_GAME });
    joinedRef.current = false;
  }, [roomId, modeAi, dispatch]);

  const handleWsMessage = useCallback((data) => {
    if (data.your_color) {
      myColorRef.current = data.your_color;
      dispatchRef.current({
        type: GAME_ACTIONS.SET_MY_COLOR,
        payload: data.your_color === 'белый' ? 'белый' : 'черный',
      });
    }
    const result = handleServerMessageRef.current(data);
    if (result?.needSync) {
      sendRef.current(buildV2SyncPayload(stateRef.current.confirmedPly));
    }
    if (result?.text) {
      showMessageRef.current(result.text, result.type);
    }
  }, []);

  const handleWsStatus = useCallback((statusInfo) => {
    if (!statusInfo) return;
    if (statusInfo.type === 'reconnecting') {
      setWsReconnecting(true);
      dispatchRef.current({ type: GAME_ACTIONS.DESELECT });
      showMessage(resolveWsErrorMessage(statusInfo.message), MSG_WARNING);
      return;
    }
    if (statusInfo.type === 'connected') {
      setWsReconnecting(false);
      const isReconnect = joinedRef.current;
      if (!joinedRef.current) {
        joinedRef.current = true;
        trackGameEvent('game_joined', { roomId, modeAi });
      }
      if (isReconnect) {
        showMessage(t('game.connectionRestored'));
      }
      if (isReconnect) {
        const s = stateRef.current;
        if (!s.waiting && !s.gameOver) {
          sendRef.current(buildV2SyncPayload(s.confirmedPly));
        }
      }
    }
  }, [showMessage, t, roomId, modeAi]);

  const handleWsError = useCallback((errorInfo) => {
    const error = typeof errorInfo === 'string'
      ? { type: 'unknown', recoverable: false, message: errorInfo }
      : errorInfo;

    if (!error?.message) return;
    const message = resolveWsErrorMessage(error.message);

    if (error.recoverable) {
      showMessage(message, MSG_WARNING);
      return;
    }

    if (ROOM_ERROR_TYPES.has(error.type)) {
      setWsReconnecting(false);
      trackGameEvent('ws_fatal_close', { roomId, type: error.type });
      dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: message });
      const delay = error.type === 'reconnect_failed' ? 4000 : 2000;
      setTimeout(() => navigate('/'), delay);
      return;
    }

    if (stateRef.current.waiting) {
      dispatchRef.current({ type: GAME_ACTIONS.SET_JOINING_ERROR, payload: message });
      return;
    }

    showMessage(message, MSG_ERROR);
  }, [navigate, showMessage, roomId]);

  const { send, setBoardRef } = useWebSocket(
    roomId,
    handleWsMessage,
    handleWsError,
    handleWsStatus,
  );

  useEffect(() => {
    sendRef.current = send;
  }, [send]);

  return { send, wsReconnecting, stateRef, setBoardRef };
}
