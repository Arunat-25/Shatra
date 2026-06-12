import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  ensureLocaleLoaded,
  getStoredLocale,
  initI18n,
  normalizeLocale,
  SELECTABLE_LOCALES,
  setStoredLocale,
} from './index';
import i18n from './index';

const LOCALE_KEY = 'shatra_locale';

describe('locale helpers', () => {
  afterEach(() => {
    localStorage.removeItem(LOCALE_KEY);
  });

  it('SELECTABLE_LOCALES exposes ru and en only', () => {
    expect(SELECTABLE_LOCALES).toEqual(['ru', 'en']);
    expect(SELECTABLE_LOCALES).not.toContain('alt');
  });

  it('normalizeLocale maps alt to ru', () => {
    expect(normalizeLocale('alt')).toBe('ru');
  });

  it('normalizeLocale keeps ru and en', () => {
    expect(normalizeLocale('ru')).toBe('ru');
    expect(normalizeLocale('en')).toBe('en');
  });

  it('normalizeLocale falls back unknown locales to ru', () => {
    expect(normalizeLocale('de')).toBe('ru');
    expect(normalizeLocale(null)).toBe('ru');
  });

  it('getStoredLocale returns ru when alt was saved', () => {
    localStorage.setItem(LOCALE_KEY, 'alt');
    expect(getStoredLocale()).toBe('ru');
  });

  it('setStoredLocale persists normalized locale', () => {
    setStoredLocale('en');
    expect(localStorage.getItem(LOCALE_KEY)).toBe('en');
    setStoredLocale('alt');
    expect(localStorage.getItem(LOCALE_KEY)).toBe('ru');
  });
});

describe('lazy locale bundles', () => {
  beforeEach(async () => {
    await initI18n();
  });

  it('ensureLocaleLoaded adds en bundle on demand', async () => {
    await ensureLocaleLoaded('en');
    expect(i18n.hasResourceBundle('en', 'translation')).toBe(true);
    expect(i18n.t('nav.home', { lng: 'en' })).toBeTruthy();
  });

  it('does not bundle alt locale', async () => {
    await ensureLocaleLoaded('alt');
    expect(i18n.hasResourceBundle('alt', 'translation')).toBe(false);
  });
});
