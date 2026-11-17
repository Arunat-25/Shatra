import useGameWebSocket from './useGameWebSocket';
import useHotseatSession from './useHotseatSession';

/**
 * Выбор сессии игры: онлайн (WebSocket) или хотсит (локальный рефери).
 * Оба хука вызываются безусловно — порядок хуков стабилен при смене режима.
 */
export default function useGameSession(modeHotseat, roomId, modeAi, deps) {
  const online = useGameWebSocket(roomId, modeAi, { ...deps, enabled: !modeHotseat });
  const local = useHotseatSession({ ...deps, enabled: modeHotseat });
  return modeHotseat ? local : online;
}
