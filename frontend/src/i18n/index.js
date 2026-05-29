import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import ru from '../locales/ru.json';
import en from '../locales/en.json';
import alt from '../locales/alt.json';

const LOCALE_KEY = 'shatra_locale';
export const SUPPORTED_LOCALES = ['ru', 'en', 'alt'];

export function normalizeLocale(locale) {
  return SUPPORTED_LOCALES.includes(locale) ? locale : 'ru';
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

i18n.use(initReactI18next).init({
  resources: {
    ru: { translation: ru },
    en: { translation: en },
    alt: { translation: alt },
  },
  lng: getStoredLocale(),
  fallbackLng: 'ru',
  interpolation: { escapeValue: false },
});

export default i18n;
