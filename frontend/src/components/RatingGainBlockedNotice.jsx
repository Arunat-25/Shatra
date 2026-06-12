import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';

export default function RatingGainBlockedNotice() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();

  const blockedUntil = user?.rating_gain_blocked_until
    ? new Date(user.rating_gain_blocked_until)
    : null;
  const isBlocked = blockedUntil != null
    && !Number.isNaN(blockedUntil.getTime())
    && blockedUntil.getTime() > Date.now();

  if (!isBlocked) return null;

  const untilLabel = blockedUntil.toLocaleString(i18n.language, {
    dateStyle: 'short',
    timeStyle: 'short',
  });

  return (
    <div className="lobby-rating-blocked" role="alert">
      <p className="lobby-rating-blocked__title">
        {t('lobby.ratingGainBlockedTitle')}
      </p>
      <p className="lobby-rating-blocked__text">
        {t('lobby.ratingGainBlockedUntil', { until: untilLabel })}
      </p>
    </div>
  );
}
