import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import useClockCountdown from '../hooks/useClockCountdown';
import { formatClockTime, getBoardSideOrder, readTimerSeconds } from '../utils';
import { playerDisplayForColor } from '../utils/playerDisplay';
import PlayerNick from './PlayerNick';
import { PieceCountRow } from './PieceCounts';

function TimerRow({
  nickname,
  title,
  rating,
  ratingDelta,
  showRating,
  showRatingDelta,
  seconds,
  isActive,
  isSelf,
  showTime,
  countsByType,
  color,
  t,
}) {
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
        <PlayerNick
          className="timer-row__nick"
          nickname={nickname}
          title={title}
          rating={rating}
          ratingDelta={ratingDelta}
          showRating={showRating}
          showRatingDelta={showRatingDelta}
        />
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
  timerSyncedAt,
  moversColor,
  myColor,
  timeControl,
  playersInfo,
  countsByType,
  middleSlot,
  showRating = false,
  gameOver = false,
  waiting = false,
}) {
  const { t } = useTranslation();
  const displayTimer = useClockCountdown({
    timer,
    timerSyncedAt,
    moversColor,
    timeControl,
    gameOver,
    waiting,
  });
  const hasTimer = Boolean(timeControl && timer);
  if (!myColor && !playersInfo?.length) return null;

  const { top, bottom } = getBoardSideOrder(myColor);
  const topSec = hasTimer ? readTimerSeconds(displayTimer, top) : null;
  const bottomSec = hasTimer ? readTimerSeconds(displayTimer, bottom) : null;
  const topDisplay = playerDisplayForColor(playersInfo, top, t, gameOver);
  const bottomDisplay = playerDisplayForColor(playersInfo, bottom, t, gameOver);

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
        nickname={topDisplay.nickname}
        title={topDisplay.title}
        rating={topDisplay.rating}
        ratingDelta={topDisplay.ratingDelta}
        showRating={showRating}
        showRatingDelta={showRating && gameOver}
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
        nickname={bottomDisplay.nickname}
        title={bottomDisplay.title}
        rating={bottomDisplay.rating}
        ratingDelta={bottomDisplay.ratingDelta}
        showRating={showRating}
        showRatingDelta={showRating && gameOver}
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
  timerSyncedAt: PropTypes.number,
  moversColor: PropTypes.string,
  myColor: PropTypes.string,
  timeControl: PropTypes.number,
  playersInfo: PropTypes.arrayOf(PropTypes.object),
  countsByType: PropTypes.object,
  middleSlot: PropTypes.node,
  showRating: PropTypes.bool,
  gameOver: PropTypes.bool,
  waiting: PropTypes.bool,
};
