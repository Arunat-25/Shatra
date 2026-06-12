import { useTranslation } from 'react-i18next';
import {
  ensureLocaleLoaded,
  getStoredLocale,
  normalizeLocale,
  SELECTABLE_LOCALES,
  setStoredLocale,
} from '../i18n';
import LocaleFlag, { LOCALE_ARIA } from './LocaleFlag';

export default function LocaleSwitcher({ compact = false }) {
  const { i18n } = useTranslation();
  const locale = normalizeLocale(i18n.language || getStoredLocale());

  const setLocale = async (lng) => {
    await ensureLocaleLoaded(lng);
    setStoredLocale(lng);
    await i18n.changeLanguage(lng);
  };

  const rootClass = [
    'locale-switcher',
    compact ? 'locale-switcher--compact' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass} role="group" aria-label="Language">
      {SELECTABLE_LOCALES.map((lng, index) => (
        <span key={lng} className="locale-switcher__item">
          {index > 0 && <span className="locale-switcher__sep" aria-hidden>|</span>}
          <button
            type="button"
            className={`locale-switcher__btn ${locale === lng ? 'is-active' : ''}`}
            onClick={() => setLocale(lng)}
            aria-label={LOCALE_ARIA[lng]}
            aria-pressed={locale === lng}
            title={LOCALE_ARIA[lng]}
          >
            <LocaleFlag locale={lng} />
          </button>
        </span>
      ))}
    </div>
  );
}
