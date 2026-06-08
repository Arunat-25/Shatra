import React from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { formatClockTime, readTimerSeconds } from '../utils';
import { playerDisplayForColor } from '../utils/playerDisplay';
import PlayerNick from './PlayerNick';
import { PieceCountRow } from './PieceCounts';

export default function PlayerBar({
  color,
  position,
  playersInfo,
  timer,
  moversColor,
  myColor,
  timeControl,
  countsByType,
  showRating = false,
  gameOver = false,
}) {
  const { t } = useTranslation();
  const hasTimer = Boolean(timeControl && timer);
  const seconds = hasTimer ? readTimerSeconds(timer, color) : null;
  const isActive = hasTimer && moversColor === color;
  const isSelf = myColor === color;
  const low = hasTimer && seconds != null && seconds <= 10;
  const { nickname, title, rating, ratingDelta } = playerDisplayForColor(
    playersInfo,
    color,
    t,
    gameOver,
  );

  return (
    <div
      className={[
        'game-player-bar',
        'game-player-bar--mobile',
        `game-player-bar--${position}`,
        isSelf ? 'game-player-bar--self' : 'game-player-bar--opponent',
      ].filter(Boolean).join(' ')}
    >
      <div className="game-player-bar__info">
        <PlayerNick
          className={['game-player-bar__nick', isSelf ? 'game-player-bar__nick--self' : ''].filter(Boolean).join(' ')}
          nickname={nickname}
          title={title}
          rating={rating}
          ratingDelta={ratingDelta}
          showRating={showRating}
          showRatingDelta={showRating && gameOver}
        />
        <PieceCountRow color={color} countsByType={countsByType} />
      </div>
      {hasTimer && (
        <span
          className={[
            'game-player-bar__time',
            isActive ? 'game-player-bar__time--active' : '',
            low ? 'game-player-bar__time--low' : '',
          ].filter(Boolean).join(' ')}
          aria-label={t('game.time')}
        >
          {formatClockTime(seconds)}
        </span>
      )}
    </div>
  );
}

PlayerBar.propTypes = {
  color: PropTypes.string.isRequired,
  position: PropTypes.oneOf(['top', 'bottom']).isRequired,
  playersInfo: PropTypes.arrayOf(PropTypes.object),
  timer: PropTypes.object,
  moversColor: PropTypes.string,
  myColor: PropTypes.string,
  timeControl: PropTypes.number,
  countsByType: PropTypes.object,
  showRating: PropTypes.bool,
  gameOver: PropTypes.bool,
};
