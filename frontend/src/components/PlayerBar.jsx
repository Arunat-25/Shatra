import React from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { COLOR_WHITE, COLOR_BLACK } from '../constants';
import { formatClockTime, readTimerSeconds } from '../utils';
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

export default function PlayerBar({
  color,
  position,
  playersInfo,
  timer,
  moversColor,
  myColor,
  timeControl,
  countsByType,
}) {
  const { t } = useTranslation();
  const hasTimer = Boolean(timeControl && timer);
  const seconds = hasTimer ? readTimerSeconds(timer, color) : null;
  const isActive = hasTimer && moversColor === color;
  const isSelf = myColor === color;
  const low = hasTimer && seconds != null && seconds <= 10;
  const nickname = nicknameForColor(playersInfo, color, t);

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
        <span
          className={['game-player-bar__nick', isSelf ? 'game-player-bar__nick--self' : ''].filter(Boolean).join(' ')}
          title={nickname}
        >
          {nickname}
        </span>
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
};
