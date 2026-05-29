import { describe, expect, it } from 'vitest';
import ru from './ru.json';
import en from './en.json';
import alt from './alt.json';

function allKeys(obj, prefix = '') {
  const keys = [];
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object' && !Array.isArray(v)) {
      keys.push(...allKeys(v, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

function get(obj, path) {
  return path.split('.').reduce((o, k) => o?.[k], obj);
}

const REQUIRED_KEYS = [
  'nav.login',
  'nav.register',
  'nav.profile',
  'nav.logout',
  'locale.ru',
  'locale.en',
  'locale.alt',
  'lobby.title',
  'lobby.anonymous',
  'lobby.join',
  'auth.loginTitle',
  'auth.changePassword',
  'auth.passwordChangedLogin',
  'game.waitingOpponent',
  'game.opponent',
  'chat.title',
  'chat.send',
  'chat.anonymous',
];

const LOCALES = { ru, en, alt };

describe('locale files', () => {
  const ruKeys = allKeys(ru);

  for (const key of REQUIRED_KEYS) {
    it(`ru has ${key}`, () => {
      expect(get(ru, key)).toBeTruthy();
    });
    for (const [name, data] of Object.entries(LOCALES)) {
      it(`${name} has ${key}`, () => {
        expect(get(data, key)).toBeTruthy();
      });
    }
  }

  for (const [name, data] of Object.entries(LOCALES)) {
    if (name === 'ru') continue;
    it(`${name} has same top-level namespaces as ru`, () => {
      expect(Object.keys(data).sort()).toEqual(Object.keys(ru).sort());
    });

    it(`${name} mirrors ru key structure (no missing keys)`, () => {
      const missing = ruKeys.filter((k) => !allKeys(data).includes(k));
      expect(missing).toEqual([]);
    });
  }

  it('en and alt locale labels differ from ru (actual translation)', () => {
    expect(ru.nav.login).not.toBe(en.nav.login);
    expect(ru.nav.login).not.toBe(alt.nav.login);
    expect(ru.chat.send).not.toBe(en.chat.send);
    expect(ru.chat.send).not.toBe(alt.chat.send);
  });

  it('alt locale has no ü/ö transliteration artifacts in Cyrillic strings', () => {
    const text = JSON.stringify(alt);
    expect(text).not.toMatch(/[üöÜÖ]/);
  });
});
