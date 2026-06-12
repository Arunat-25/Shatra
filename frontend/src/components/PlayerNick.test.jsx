import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import PlayerNick from './PlayerNick';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key, opts) => {
      if (key === 'game.playerRatingAria') {
        return `Рейтинг ${opts.rating}`;
      }
      return key;
    },
  }),
}));

describe('PlayerNick rating display', () => {
  afterEach(() => {
    cleanup();
  });

  it('shows rating without border class on rating element', () => {
    const { container } = render(
      <PlayerNick
        nickname="alice"
        rating={1542}
        showRating
      />,
    );
    const rating = container.querySelector('.game-player-nick__rating');
    expect(rating).toBeTruthy();
    expect(rating.textContent).toBe('1542');
    expect(rating.className).not.toMatch(/border/i);
  });

  it('shows green gain delta when game over', () => {
    const { container } = render(
      <PlayerNick
        nickname="alice"
        rating={1510}
        ratingDelta={10}
        showRating
        showRatingDelta
      />,
    );
    const delta = container.querySelector('.game-player-nick__rating-delta--gain');
    expect(delta).toBeTruthy();
    expect(delta.textContent).toBe('+10');
  });

  it('shows red loss delta when game over', () => {
    const { container } = render(
      <PlayerNick
        nickname="bob"
        rating={1490}
        ratingDelta={-5}
        showRating
        showRatingDelta
      />,
    );
    const delta = container.querySelector('.game-player-nick__rating-delta--loss');
    expect(delta).toBeTruthy();
    expect(delta.textContent).toBe('-5');
  });

  it('hides delta until showRatingDelta is enabled', () => {
    render(
      <PlayerNick
        nickname="bob"
        rating={1510}
        ratingDelta={10}
        showRating
        showRatingDelta={false}
      />,
    );
    expect(screen.queryByText('+10')).toBeNull();
  });
});
