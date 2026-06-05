import { describe, expect, it } from 'vitest';
import { canShowPassTurn, passTurnColor } from './passTurn';

describe('canShowPassTurn', () => {
  it('shows during biy chain only for the mover', () => {
    const state = {
      canPass: true,
      myColor: 'белый',
      moversColor: 'белый',
      posForMandatoryCapture: 19,
    };
    expect(canShowPassTurn(state)).toBe(true);
    expect(canShowPassTurn({ ...state, myColor: 'черный' })).toBe(false);
  });

  it('after final biy capture shows for the capturer, not the next mover', () => {
    const state = {
      canPass: true,
      myColor: 'белый',
      moversColor: 'черный',
      posForMandatoryCapture: null,
    };
    expect(canShowPassTurn(state)).toBe(true);
    expect(canShowPassTurn({ ...state, myColor: 'черный' })).toBe(false);
  });

  it('hidden when pass is not offered', () => {
    expect(
      canShowPassTurn({
        canPass: false,
        myColor: 'белый',
        moversColor: 'белый',
        posForMandatoryCapture: 19,
      }),
    ).toBe(false);
  });
});

describe('passTurnColor', () => {
  it('uses movers color during chain', () => {
    expect(
      passTurnColor({ moversColor: 'белый', posForMandatoryCapture: 19 }),
    ).toBe('белый');
  });

  it('uses opponent after chain ended', () => {
    expect(
      passTurnColor({ moversColor: 'черный', posForMandatoryCapture: null }),
    ).toBe('белый');
  });
});
