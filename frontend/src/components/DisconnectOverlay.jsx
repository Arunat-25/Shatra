import { useTranslation } from 'react-i18next';

export default function DisconnectOverlay({ disconnectCountdown }) {
  const { t } = useTranslation();

  return (
    <div className="opponent-disconnected-overlay">
      <div className="opponent-disconnected-modal">
        <div className="opponent-disconnected-icon">📡</div>
        <h3 className="opponent-disconnected-title">{t('disconnect.title')}</h3>
        <p className="opponent-disconnected-text">
          {t('disconnect.text')}
        </p>
        <div className="opponent-disconnected-countdown">
          <span className="countdown-number">{disconnectCountdown}</span>
          <span className="countdown-label">{t('disconnect.seconds')}</span>
        </div>
      </div>
    </div>
  );
}
