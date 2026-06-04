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
  'nav.home',
  'nav.login',
  'nav.register',
  'nav.profile',
  'nav.logout',
  'nav.tutorial',
  'tutorial.pageTitle',
  'tutorial.section1.title',
  'tutorial.section1.step1.text',
  'tutorial.section1.step2.text',
  'tutorial.section1.step3.text',
  'tutorial.section1.step4.text',
  'tutorial.section1.step5.text',
  'tutorial.section1.step6.text',
  'tutorial.section1.step7.text',
  'tutorial.section1.step8.text',
  'tutorial.section1.step9.text',
  'tutorial.section1.step10.text',
  'tutorial.section1.step11.text',
  'tutorial.section1.step12.text',
  'tutorial.section1.step13.text',
  'tutorial.section1.step14.text',
  'tutorial.next',
  'tutorial.prev',
  'tutorial.tryAgain',
  'tutorial.passTurn',
  'tutorial.section2.title',
  'tutorial.section2.step1.text',
  'tutorial.section2.step2.text',
  'tutorial.section2.step3.text',
  'tutorial.section2.step4.text',
  'tutorial.section2.step5.text',
  'tutorial.section2.winCaptureSelectHint',
  'tutorial.section2.step6.text',
  'tutorial.section2.promoWhiteSelectHint',
  'tutorial.section2.promoBlackSelectHint',
  'tutorial.section3.title',
  'tutorial.section3.step1.text',
  'tutorial.section3.step2.text',
  'tutorial.section3.step3.text',
  'tutorial.section3.step4.text',
  'tutorial.section4.title',
  'tutorial.section4.step1.text',
  'tutorial.section4.step2.text',
  'tutorial.section4.step3.text',
  'tutorial.section5.title',
  'tutorial.section5.step1.text',
  'tutorial.section5.deployHint',
  'tutorial.section5.deployTargetHint',
  'tutorial.section5.mainFieldBlockedHint',
  'tutorial.section5.fortressOrderHint',
  'tutorial.section5.fortressNoMoveHint',
  'tutorial.section5.step2.text',
  'tutorial.section5.captureSelectHint',
  'tutorial.section5.captureTargetHint',
  'tutorial.section5.captureWrongPieceHint',
  'tutorial.section5.captureAfterHint',
  'tutorial.section5.step3.text',
  'tutorial.section5.biyBatyrSelectHint',
  'tutorial.section5.biyBatyrTargetHint',
  'tutorial.section5.biyBatyrNoMovesHint',
  'tutorial.section5.step4.text',
  'tutorial.section5.step4SelectHint',
  'tutorial.section5.step4ChainHint',
  'tutorial.section5.step5.text',
  'tutorial.section5.shatraFortressSelectHint',
  'tutorial.section5.step6.text',
  'tutorial.section5.reserveDeploySelectHint',
  'tutorial.section5.reserveDeployTargetHint',
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
  'chat.hide',
  'chat.show',
  'lobby.onlineCount',
  'lobby.activeGamesCount',
  'auth.gamesTitle',
  'game.qrLabel',
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
