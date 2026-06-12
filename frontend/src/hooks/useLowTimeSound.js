import { useEffect, useRef } from 'react';
import { computeDisplayTimer } from '../game/clockUtils';
import { readTimerSeconds } from '../utils';
import { getEffectiveVolume } from '../audio/soundSettings';
import { playLowTime } from '../audio/gameSounds';

const LOW_TIME_SEC = 10;

/** Play once when own clock crosses from above 10s to 10s or below — no parent re-renders. */
export default function useLowTimeSound({
  timeControl,
  timer,
  timerSyncedAt,
  moversColor,
  myColor,
  gameOver,
  waiting,
}) {
  const warnedRef = useRef(false);

  useEffect(() => {
    if (!timeControl || !timer || !myColor || gameOver || waiting) {
      warnedRef.current = false;
      return undefined;
    }

    const check = () => {
      const display = computeDisplayTimer({
        timer,
        timerSyncedAt,
        moversColor,
        timeControl,
        gameOver,
        waiting,
      });
      const sec = readTimerSeconds(display, myColor);
      if (sec == null) return;

      if (sec > LOW_TIME_SEC) {
        warnedRef.current = false;
        return;
      }

      if (!warnedRef.current && getEffectiveVolume() > 0) {
        warnedRef.current = true;
        playLowTime();
      }
    };

    check();
    const id = setInterval(check, 1000);
    return () => clearInterval(id);
  }, [timeControl, timer, timerSyncedAt, moversColor, myColor, gameOver, waiting]);
}
