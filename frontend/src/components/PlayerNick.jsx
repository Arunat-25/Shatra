import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';

function formatDelta(delta) {
  if (delta > 0) return `+${delta}`;
  return String(delta);
}

/** Nickname + optional visible Elo (PvP 1v1). */
export default function PlayerNick({
  nickname,
  title,
  rating,
  ratingDelta,
  showRating,
  showRatingDelta,
  className,
}) {
  const { t } = useTranslation();
  const showDelta = showRatingDelta && ratingDelta != null;

  return (
    <span className={className} title={title}>
      <span className="game-player-nick__name">{nickname}</span>
      {showRating && rating != null && (
        <span className="game-player-nick__rating-group">
          <span
            className="game-player-nick__rating"
            aria-label={t('game.playerRatingAria', { rating })}
          >
            {rating}
          </span>
          {showDelta && (
            <span
              className={[
                'game-player-nick__rating-delta',
                ratingDelta >= 0
                  ? 'game-player-nick__rating-delta--gain'
                  : 'game-player-nick__rating-delta--loss',
              ].join(' ')}
            >
              {formatDelta(ratingDelta)}
            </span>
          )}
        </span>
      )}
    </span>
  );
}

PlayerNick.propTypes = {
  nickname: PropTypes.string.isRequired,
  title: PropTypes.string,
  rating: PropTypes.number,
  ratingDelta: PropTypes.number,
  showRating: PropTypes.bool,
  showRatingDelta: PropTypes.bool,
  className: PropTypes.string,
};

PlayerNick.defaultProps = {
  title: undefined,
  rating: null,
  ratingDelta: null,
  showRating: false,
  showRatingDelta: false,
  className: '',
};
