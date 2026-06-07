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

  it('hidden after single biy capture when chain cannot continue', () => {
    expect(
      canShowPassTurn({
        canPass: false,
        myColor: 'белый',
        moversColor: 'черный',
        posForMandatoryCapture: null,
      }),
    ).toBe(false);
  });

  it('hidden when canPass true but not in active chain cell', () => {
    expect(
      canShowPassTurn({
        canPass: true,
        myColor: 'белый',
        moversColor: 'белый',
        posForMandatoryCapture: null,
      }),
    ).toBe(false);
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

  it('returns null when not in capture chain', () => {
    expect(
      passTurnColor({ moversColor: 'черный', posForMandatoryCapture: null }),
    ).toBe(null);
  });
});
