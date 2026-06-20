import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { MSG_ERROR, MSG_WARNING, ROOM_AI, ROOM_PUBLIC } from '../constants';
import { createRoom } from '../api';
import { GAME_ACTIONS } from './useGameReducer';
import {
  buildDeclineDrawPayload,
  buildOfferDrawPayload,
  buildPassPayload,
  buildRequestRematchPayload,
  buildResignPayload,
  buildCancelGamePayload,
  buildChatPayload,
} from '../utils/wsPayloads';

const RESIGN_ARM_MS = 4000;

export default function useGameActions({
  send,
  showMessage,
  modeAi,
  navigate,
  dispatch,
  stateRef,
  state,
}) {
  const { t } = useTranslation();
  const [resignArmed, setResignArmed] = useState(false);
  const resignArmedRef = useRef(false);

  useEffect(() => {
    resignArmedRef.current = resignArmed;
  }, [resignArmed]);

  useEffect(() => {
    if (!resignArmed) return undefined;
    const timer = setTimeout(() => {
      resignArmedRef.current = false;
      setResignArmed(false);
    }, RESIGN_ARM_MS);
    return () => clearTimeout(timer);
  }, [resignArmed]);

  useEffect(() => {
    if (state.gameOver) {
      resignArmedRef.current = false;
      setResignArmed(false);
    }
  }, [state.gameOver]);

  const goToLobby = useCallback(() => navigate('/'), [navigate]);

  const skipTurn = useCallback(() => {
    send(buildPassPayload(stateRef.current));
    dispatch({ type: GAME_ACTIONS.CLEAR_CAN_PASS });
  }, [send, dispatch, stateRef]);

  const handleResignClick = useCallback(() => {
    if (!resignArmedRef.current) {
      resignArmedRef.current = true;
      setResignArmed(true);
      return;
    }
    resignArmedRef.current = false;
    setResignArmed(false);
    if (stateRef.current.gameOver) return;
    send(buildResignPayload());
  }, [send, stateRef]);

  const offerDraw = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver) return;
    if (s.drawOfferFrom === s.myColor) return;
    if (!send(buildOfferDrawPayload())) {
      showMessage(t('game.connectionLost'), MSG_WARNING);
    }
  }, [send, showMessage, stateRef, t]);

  const acceptDraw = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver) return;
    if (!s.drawOfferFrom || s.drawOfferFrom === s.myColor) return;
    if (!send(buildOfferDrawPayload())) {
      showMessage(t('game.connectionLost'), MSG_WARNING);
    }
  }, [send, showMessage, stateRef, t]);

  const declineDraw = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver) return;
    if (!s.drawOfferFrom || s.drawOfferFrom === s.myColor) return;
    send(buildDeclineDrawPayload());
  }, [send, stateRef]);

  const cancelGame = useCallback(() => {
    const s = stateRef.current;
    if (s.gameOver || modeAi) return;
    if (s.movesHistory.some((m) => m.mover === s.myColor)) return;
    dispatch({
      type: GAME_ACTIONS.GAME_CANCELLED,
      payload: { message_code: 'cancel.you' },
    });
    if (!send(buildCancelGamePayload())) {
      showMessage(t('game.connectionLost'), MSG_WARNING);
    }
  }, [modeAi, send, showMessage, dispatch, stateRef, t]);

  const playAgain = useCallback(async () => {
    try {
      if (modeAi) {
        const data = await createRoom(ROOM_AI, null, null, 'random');
        navigate(`/${data.room_id}?mode=ai`, { replace: true });
        return;
      }
      const data = await createRoom(
        ROOM_PUBLIC,
        stateRef.current.timeControl,
        stateRef.current.increment,
      );
      navigate(`/${data.room_id}`, { replace: true });
    } catch (e) {
      showMessage(e?.message || t('game.createNewFailed'), MSG_ERROR);
    }
  }, [modeAi, navigate, showMessage, stateRef, t]);

  const sendChat = useCallback((text) => {
    send(buildChatPayload(text));
  }, [send]);

  const toggleChatHidden = useCallback(() => {
    dispatch({ type: GAME_ACTIONS.TOGGLE_CHAT_HIDDEN });
  }, [dispatch]);

  const requestRematch = useCallback(() => {
    const s = stateRef.current;
    if (!s.gameOver || modeAi || s.rematchReady || s.rematchUnavailable) return;
    const ok = send(buildRequestRematchPayload());
    if (!ok) {
      showMessage(t('game.connectionLost'), MSG_WARNING);
      return;
    }
    dispatch({
      type: GAME_ACTIONS.SET_REMATCH_STATUS,
      payload: { self_ready: true, opponent_ready: s.rematchOpponentReady },
    });
  }, [modeAi, send, showMessage, dispatch, stateRef, t]);

  const drawPending = state.drawOfferFrom != null && state.drawOfferFrom === state.myColor;
  const drawIncoming = state.drawOfferFrom != null && state.drawOfferFrom !== state.myColor;
  const canCancelGame = !modeAi
    && !state.gameOver
    && !!state.myColor
    && !drawIncoming
    && !state.movesHistory.some((m) => m.mover === state.myColor);

  return {
    goToLobby,
    skipTurn,
    handleResignClick,
    resignArmed,
    offerDraw,
    acceptDraw,
    declineDraw,
    cancelGame,
    playAgain,
    sendChat,
    toggleChatHidden,
    requestRematch,
    drawPending,
    drawIncoming,
    canCancelGame,
  };
}
