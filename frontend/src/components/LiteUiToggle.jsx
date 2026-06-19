import { useTranslation } from 'react-i18next';
import { useLiteUi } from '../context/LiteUiContext';

function IconLiteUi() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M12 3v2" />
      <path d="M12 19v2" />
      <path d="M5.6 5.6l1.4 1.4" />
      <path d="M17 17l1.4 1.4" />
      <path d="M3 12h2" />
      <path d="M19 12h2" />
      <path d="M5.6 18.4l1.4-1.4" />
      <path d="M17 7l1.4-1.4" />
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
}

export default function LiteUiToggle({ variant = 'icon' }) {
  const { t } = useTranslation();
  const { enabled, toggle } = useLiteUi();
  const label = enabled ? t('nav.liteUiOn') : t('nav.liteUiOff');

  if (variant === 'drawer') {
    return (
      <button
        type="button"
        className={`app-nav-drawer__link${enabled ? ' is-active' : ''}`}
        onClick={toggle}
        aria-pressed={enabled}
        aria-label={label}
        title={label}
      >
        {t('nav.liteUi')}
      </button>
    );
  }

  return (
    <button
      type="button"
      className={`app-auth-nav__icon-btn app-lite-ui-toggle${enabled ? ' is-active' : ''}`}
      onClick={toggle}
      aria-pressed={enabled}
      aria-label={label}
      title={label}
    >
      <IconLiteUi />
    </button>
  );
}
