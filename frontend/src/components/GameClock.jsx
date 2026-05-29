import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { COLOR_WHITE, COLOR_BLACK } from '../constants';
import { formatClockTime, getBoardSideOrder, readTimerSeconds } from '../utils';
import { PieceCountRow } from './PieceCounts';

function nicknameForColor(playersInfo, color, t) {
  const player = playersInfo?.find((p) => p.color === color);
  if (!player) {
    return color === COLOR_WHITE ? t('colors.whitePl') : t('colors.blackPl');
  }
  if (player.display_name) return player.display_name;
  if (!player.is_anonymous && player.username) return player.username;
  return t('lobby.anonymous');
}

function TimerRow({ nickname, seconds, isActive, isSelf, showTime, countsByType, color, t }) {
  const low = showTime && seconds != null && seconds <= 10;
  return (
    <div
      className={[
        'timer-row',
        !showTime ? 'timer-row--names-only' : '',
        isActive && showTime ? 'timer-row--active' : '',
        isSelf ? 'timer-row--self' : '',
      ].filter(Boolean).join(' ')}
    >
      <div className="timer-row__left">
        <span className="timer-row__nick" title={nickname}>
          {nickname}
        </span>
        {countsByType && color && (
          <div className="timer-row__counts" aria-label={t('game.pieces')}>
            <PieceCountRow color={color} countsByType={countsByType} />
          </div>
        )}
      </div>

      {showTime && (
        <span
          className={[
            'timer-row__time',
            isActive ? 'timer-row__time--active' : '',
            low ? 'timer-row__time--low' : '',
          ].filter(Boolean).join(' ')}
        >
          {formatClockTime(seconds)}
        </span>
      )}
    </div>
  );
}

export default function GameClock({
  timer,
  moversColor,
  myColor,
  timeControl,
  playersInfo,
  countsByType,
  middleSlot,
}) {
  const { t } = useTranslation();
  const hasTimer = Boolean(timeControl && timer);
  if (!myColor && !playersInfo?.length) return null;

  const { top, bottom } = getBoardSideOrder(myColor);
  const topSec = hasTimer ? readTimerSeconds(timer, top) : null;
  const bottomSec = hasTimer ? readTimerSeconds(timer, bottom) : null;

  return (
    <div
      className={[
        'timer-display',
        'timer-display--game',
        hasTimer ? '' : 'timer-display--names-only',
      ].filter(Boolean).join(' ')}
      aria-label={hasTimer ? t('game.clocks') : t('game.players')}
    >
      <TimerRow
        nickname={nicknameForColor(playersInfo, top, t)}
        seconds={topSec}
        isActive={hasTimer && moversColor === top}
        isSelf={myColor === top}
        showTime={hasTimer}
        countsByType={countsByType}
        color={top}
        t={t}
      />
      {middleSlot && (
        <div className="timer-display__middle">
          {middleSlot}
        </div>
      )}
      <TimerRow
        nickname={nicknameForColor(playersInfo, bottom, t)}
        seconds={bottomSec}
        isActive={hasTimer && moversColor === bottom}
        isSelf={myColor === bottom}
        showTime={hasTimer}
        countsByType={countsByType}
        color={bottom}
        t={t}
      />
    </div>
  );
}

GameClock.propTypes = {
  timer: PropTypes.object,
  moversColor: PropTypes.string,
  myColor: PropTypes.string,
  timeControl: PropTypes.number,
  playersInfo: PropTypes.arrayOf(PropTypes.object),
  countsByType: PropTypes.object,
  middleSlot: PropTypes.node,
};
