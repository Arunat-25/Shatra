import { useTranslation } from 'react-i18next';
import { useLiteUi } from '../context/LiteUiContext';

function IconLiteBoard() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M12 4v16" />
      <path d="M4 12h16" />
    </svg>
  );
}

export default function LiteUiToggle() {
  const { t } = useTranslation();
  const { enabled, toggle } = useLiteUi();
  const label = enabled ? t('nav.liteUiOn') : t('nav.liteUiOff');

  return (
    <button
      type="button"
      className={`app-auth-nav__icon-btn app-lite-ui-toggle${enabled ? ' is-active' : ''}`}
      onClick={toggle}
      aria-pressed={enabled}
      aria-label={label}
      title={label}
    >
      <IconLiteBoard />
    </button>
  );
}
