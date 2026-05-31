import { useEffect, useRef } from 'react';
import { readTimerSeconds } from '../utils';
import { getEffectiveVolume } from '../audio/soundSettings';
import { playLowTime } from '../audio/gameSounds';

const LOW_TIME_SEC = 10;

/** Play once when own clock crosses from above 10s to 10s or below. */
export default function useLowTimeSound({ timeControl, timer, myColor, gameOver, waiting }) {
  const warnedRef = useRef(false);

  useEffect(() => {
    if (!timeControl || !timer || !myColor || gameOver || waiting) {
      warnedRef.current = false;
      return;
    }

    const sec = readTimerSeconds(timer, myColor);
    if (sec == null) return;

    if (sec > LOW_TIME_SEC) {
      warnedRef.current = false;
      return;
    }

    if (!warnedRef.current && getEffectiveVolume() > 0) {
      warnedRef.current = true;
      playLowTime();
    }
  }, [timeControl, timer, myColor, gameOver, waiting]);
}
