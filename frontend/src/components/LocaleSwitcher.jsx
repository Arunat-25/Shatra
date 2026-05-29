import { useTranslation } from 'react-i18next';
import { getStoredLocale, normalizeLocale, setStoredLocale } from '../i18n';

const LOCALES = ['ru', 'en', 'alt'];

export default function LocaleSwitcher({ compact = false }) {
  const { t, i18n } = useTranslation();
  const locale = normalizeLocale(i18n.language || getStoredLocale());

  const setLocale = (lng) => {
    setStoredLocale(lng);
    i18n.changeLanguage(lng);
  };

  const rootClass = [
    'locale-switcher',
    compact ? 'locale-switcher--compact' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} role="group" aria-label="Language">
      {LOCALES.map((lng, index) => (
        <span key={lng} className="locale-switcher__item">
          {index > 0 && <span className="locale-switcher__sep" aria-hidden>|</span>}
          <button
            type="button"
            className={`locale-switcher__btn ${locale === lng ? 'is-active' : ''}`}
            onClick={() => setLocale(lng)}
          >
            {t(`locale.${lng}`)}
          </button>
        </span>
      ))}
    </div>
  );
}
