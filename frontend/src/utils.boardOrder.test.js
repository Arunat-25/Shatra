import { describe, expect, it } from 'vitest';
import { COLOR_WHITE, COLOR_BLACK } from './constants';
import { getBoardSideOrder, readTimerSeconds } from './utils';

describe('getBoardSideOrder', () => {
  it('white player: opponent (black) on top', () => {
    expect(getBoardSideOrder(COLOR_WHITE)).toEqual({
      top: COLOR_BLACK,
      bottom: COLOR_WHITE,
    });
  });

  it('black player: opponent (white) on top', () => {
    expect(getBoardSideOrder(COLOR_BLACK)).toEqual({
      top: COLOR_WHITE,
      bottom: COLOR_BLACK,
    });
  });

  it('readTimerSeconds supports Russian keys', () => {
    expect(readTimerSeconds({ белый: 10, черный: 20 }, COLOR_WHITE)).toBe(10);
    expect(readTimerSeconds({ white: 5, black: 7 }, COLOR_BLACK)).toBe(7);
  });
});
