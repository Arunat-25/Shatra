import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';

export default function GameResultActions({
  modeAi,
  onLobby,
  onPlayAgain,
  onRematch,
  rematchReady,
  rematchOpponentReady,
  rematchUnavailable,
}) {
  const { t } = useTranslation();

  return (
    <div className="game-result-actions game-result-actions--bar">
      <button type="button" className="game-result-btn game-result-btn--primary" onClick={onLobby}>
        {t('result.toLobby')}
      </button>
      <button
        type="button"
        className="game-result-btn game-result-btn--secondary"
        onClick={onPlayAgain}
        title={t('result.newGameTitle')}
      >
        {t('result.newGame')}
      </button>
      {!modeAi && (
        <button
          type="button"
          className={[
            'game-result-btn',
            'game-result-btn--rematch',
            !rematchUnavailable && (rematchReady || rematchOpponentReady)
              ? 'game-result-btn--rematch-pulse'
              : '',
            rematchUnavailable ? 'game-result-btn--rematch-unavailable' : '',
          ].filter(Boolean).join(' ')}
          onClick={onRematch}
          disabled={rematchReady || rematchUnavailable}
          title={
            rematchUnavailable
              ? t('result.rematchOpponentLeft')
              : rematchReady
                ? t('result.rematchWaiting')
                : rematchOpponentReady
                  ? t('result.rematchOpponentReady')
                  : t('result.rematch')
          }
        >
          {t('result.rematch')}
        </button>
      )}
    </div>
  );
}

GameResultActions.propTypes = {
  modeAi: PropTypes.bool,
  onLobby: PropTypes.func.isRequired,
  onPlayAgain: PropTypes.func.isRequired,
  onRematch: PropTypes.func.isRequired,
  rematchReady: PropTypes.bool,
  rematchOpponentReady: PropTypes.bool,
  rematchUnavailable: PropTypes.bool,
};
