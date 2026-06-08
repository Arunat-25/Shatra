import { describe, expect, it } from 'vitest';
import { COLOR_WHITE } from '../constants';
import {
  playerDisplayForColor,
  playerHoverTitle,
  playerNickname,
} from './playerDisplay';

const t = (key, opts) => {
  if (key === 'game.playerRatingTooltip') {
    return `${opts.name} · рейтинг ${opts.rating}`;
  }
  const map = {
    'colors.whitePl': 'Белые',
    'lobby.anonymous': 'Аноним',
  };
  return map[key] ?? key;
};

describe('playerDisplay', () => {
  it('shows rating in hover title for registered user', () => {
    const player = { username: 'alice', is_anonymous: false, rating: 1542 };
    expect(playerHoverTitle(player, 'alice', t)).toBe('alice · рейтинг 1542');
  });

  it('hides rating for anonymous', () => {
    expect(playerHoverTitle({ is_anonymous: true }, 'Аноним', t)).toBe('Аноним');
  });

  it('playerDisplayForColor builds nick and title', () => {
    const info = [{
      color: COLOR_WHITE,
      username: 'bob',
      is_anonymous: false,
      rating: 1510,
      rating_delta: 10,
    }];
    const { nickname, title, rating, ratingDelta } = playerDisplayForColor(
      info,
      COLOR_WHITE,
      t,
      true,
    );
    expect(nickname).toBe('bob');
    expect(title).toBe('bob · рейтинг 1510');
    expect(rating).toBe(1510);
    expect(ratingDelta).toBe(10);
  });

  it('hides rating delta until game over', () => {
    const info = [{
      color: COLOR_WHITE,
      username: 'bob',
      is_anonymous: false,
      rating: 1510,
      rating_delta: 10,
    }];
    const { ratingDelta } = playerDisplayForColor(info, COLOR_WHITE, t, false);
    expect(ratingDelta).toBeNull();
  });

  it('playerNickname falls back to color label', () => {
    expect(playerNickname(null, COLOR_WHITE, t)).toBe('Белые');
  });
});
