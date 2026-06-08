import { useEffect, useState } from 'react';
import { readTimerSeconds } from '../utils';

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
    if (!timeControl || !timer || gameOver || waiting) {
      setDisplayTimer(timer);
      return undefined;
    }

    const compute = () => {
      if (!timer || timerSyncedAt == null) return timer;
      const elapsedSec = (Date.now() - timerSyncedAt) / 1000;
      const next = { ...timer };
      if (moversColor === 'белый' && next.белый != null) {
        next.белый = Math.max(0, Number(next.белый) - elapsedSec);
      } else if (moversColor === 'черный' && next.черный != null) {
        next.черный = Math.max(0, Number(next.черный) - elapsedSec);
      }
      return next;
    };

    setDisplayTimer(compute());
    const id = setInterval(() => setDisplayTimer(compute()), 100);
    return () => clearInterval(id);
  }, [timer, timerSyncedAt, moversColor, timeControl, gameOver, waiting]);

  return displayTimer;
}

export { readTimerSeconds };
