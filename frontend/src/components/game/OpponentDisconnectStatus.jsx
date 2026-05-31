import React from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';

export default function OpponentDisconnectStatus({ disconnectCountdown, placement }) {
  const { t } = useTranslation();

  return (
    <div
      className={`opponent-disconnect-status opponent-disconnect-status--${placement}`}
      role="status"
      aria-live="polite"
    >
      <div className="opponent-disconnect-status__card">
        <div className="opponent-disconnect-status__icon" aria-hidden>📡</div>
        <h3 className="opponent-disconnect-status__title">{t('disconnect.title')}</h3>
        <p className="opponent-disconnect-status__text">{t('disconnect.text')}</p>
        <div className="opponent-disconnect-status__countdown">
          <span className="opponent-disconnect-status__number">{disconnectCountdown}</span>
          <span className="opponent-disconnect-status__label">{t('disconnect.seconds')}</span>
        </div>
      </div>
    </div>
  );
}

OpponentDisconnectStatus.propTypes = {
  disconnectCountdown: PropTypes.number.isRequired,
  placement: PropTypes.oneOf(['sidebar', 'board-edge']).isRequired,
};
