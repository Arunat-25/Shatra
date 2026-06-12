import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const LOCALE_KEY = 'shatra_locale';
export const ALL_LOCALES = ['ru', 'en', 'alt'];
/** Locales shown in the language switcher (alt hidden until translation is ready). */
export const SELECTABLE_LOCALES = ['ru', 'en'];

const localeLoaders = {
  ru: () => import('../locales/ru.json'),
  en: () => import('../locales/en.json'),
};

export function normalizeLocale(locale) {
  if (!locale || locale === 'alt') return 'ru';
  return SELECTABLE_LOCALES.includes(locale) ? locale : 'ru';
}

export function getStoredLocale() {
  try {
    if (typeof localStorage !== 'undefined') {
      return normalizeLocale(localStorage.getItem(LOCALE_KEY));
    }
  } catch {
    // SSR / test environments
  }
  return 'ru';
}

export function setStoredLocale(locale) {
  localStorage.setItem(LOCALE_KEY, normalizeLocale(locale));
}

export async function ensureLocaleLoaded(locale) {
  const lng = normalizeLocale(locale);
  if (!localeLoaders[lng]) return lng;
  if (i18n.hasResourceBundle(lng, 'translation')) return lng;
  const mod = await localeLoaders[lng]();
  i18n.addResourceBundle(lng, 'translation', mod.default, true, true);
  return lng;
}

export async function initI18n() {
  const lng = getStoredLocale();
  const mod = await localeLoaders[lng]();
  if (!i18n.isInitialized) {
    await i18n.use(initReactI18next).init({
      resources: { [lng]: { translation: mod.default } },
      lng,
      fallbackLng: 'ru',
      interpolation: { escapeValue: false },
    });
  }
  if (lng !== 'ru') {
    void ensureLocaleLoaded('ru');
  }
}

export default i18n;
