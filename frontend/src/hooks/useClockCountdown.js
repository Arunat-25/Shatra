import { useEffect, useState } from 'react';
import { computeDisplayTimer } from '../game/clockUtils';

/**
 * Smooth local countdown between server clock syncs (Lichess-style).
 * Active player's display time decreases continuously; opponent stays at last sync value.
 */
export default function useClockCountdown({
  timer,
  timerSyncedAt,
  moversColor,
  timeControl,
  gameOver,
  waiting,
}) {
  const [displayTimer, setDisplayTimer] = useState(timer);

  useEffect(() => {
    const compute = () => computeDisplayTimer({
      timer,
      timerSyncedAt,
      moversColor,
      timeControl,
      gameOver,
      waiting,
    });

    if (!timeControl || !timer || gameOver || waiting) {
      setDisplayTimer(timer);
      return undefined;
    }

    setDisplayTimer(compute());
    const id = setInterval(() => setDisplayTimer(compute()), 100);
    return () => clearInterval(id);
  }, [timer, timerSyncedAt, moversColor, timeControl, gameOver, waiting]);

  return displayTimer;
}

export { computeDisplayTimer } from '../game/clockUtils';
