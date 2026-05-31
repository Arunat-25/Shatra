/** Small flag icons for the locale switcher (decorative; use aria-label on the button). */

const FLAG_CLASS = 'locale-switcher__flag';
const VB = '0 0 60 36';

export const LOCALE_ARIA = {
  ru: 'Русский',
  en: 'English',
  alt: 'Алтайский',
};

export default function LocaleFlag({ locale }) {
  switch (locale) {
    case 'ru':
      return (
        <svg className={FLAG_CLASS} viewBox={VB} aria-hidden>
          <rect width="60" height="12" fill="#fff" />
          <rect y="12" width="60" height="12" fill="#0039a6" />
          <rect y="24" width="60" height="12" fill="#d52b1e" />
        </svg>
      );
    case 'en':
      return (
        <svg className={FLAG_CLASS} viewBox={VB} aria-hidden>
          <rect width="60" height="36" fill="#012169" />
          <path d="M0,0 L60,36 M60,0 L0,36" stroke="#fff" strokeWidth="7.2" />
          <path d="M0,0 L60,36 M60,0 L0,36" stroke="#c8102e" strokeWidth="4.8" />
          <path d="M30,0 V36 M0,18 H60" stroke="#fff" strokeWidth="12" />
          <path d="M30,0 V36 M0,18 H60" stroke="#c8102e" strokeWidth="7.2" />
        </svg>
      );
    case 'alt':
      return (
        <svg className={FLAG_CLASS} viewBox={VB} aria-hidden>
          <rect width="60" height="24.12" fill="#fff" />
          <rect y="24.12" width="60" height="1.44" fill="#3399ff" />
          <rect y="25.56" width="60" height="1.44" fill="#fff" />
          <rect y="27" width="60" height="9" fill="#3399ff" />
        </svg>
      );
    default:
      return null;
  }
}
