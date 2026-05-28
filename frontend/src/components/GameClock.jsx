import PropTypes from 'prop-types';
import { COLOR_WHITE, COLOR_BLACK } from '../constants';
import { formatClockTime } from '../utils';

function ClockItem({ label, seconds, isActive, lowThreshold = 10 }) {
  const low = seconds != null && seconds <= lowThreshold;
  return (
    <span
      className={[
        'timer-item',
        isActive ? 'timer-active' : '',
        low ? 'timer-low' : '',
      ].filter(Boolean).join(' ')}
      title={label}
    >
      {formatClockTime(seconds)}
    </span>
  );
}

export default function GameClock({ timer, moversColor, myColor, timeControl }) {
  if (!timeControl || !timer) return null;

  const whiteSec = timer[COLOR_WHITE] ?? timer.white;
  const blackSec = timer[COLOR_BLACK] ?? timer.black;

  return (
    <div className="timer-display" aria-label="Часы">
      <ClockItem
        label="Белые"
        seconds={whiteSec}
        isActive={moversColor === COLOR_WHITE}
      />
      <span className="timer-separator">|</span>
      <ClockItem
        label="Чёрные"
        seconds={blackSec}
        isActive={moversColor === COLOR_BLACK}
      />
      {myColor && (
        <span className="timer-you" title="Ваш цвет">
          {myColor === COLOR_WHITE ? '⚪' : '⚫'}
        </span>
      )}
    </div>
  );
}

GameClock.propTypes = {
  timer: PropTypes.object,
  moversColor: PropTypes.string,
  myColor: PropTypes.string,
  timeControl: PropTypes.number,
};
