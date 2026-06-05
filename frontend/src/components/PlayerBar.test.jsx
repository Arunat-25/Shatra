import React from 'react';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import PlayerBar from './PlayerBar';
import { COLOR_WHITE } from '../constants';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => {
      const map = {
        'colors.whitePl': 'Белые',
        'lobby.anonymous': 'Аноним',
        'game.time': 'Время',
      };
      return map[key] ?? key;
    },
  }),
}));

vi.mock('./PieceCounts', () => ({
  PieceCountRow: () => (
    <div className="room-counts-row room-counts-row--inline">
      <span className="room-counts-num">2</span>
      <span className="room-counts-num">7</span>
    </div>
  ),
}));

describe('PlayerBar mobile layout', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders nick, piece counts and timer in one bar row', () => {
    const { container } = render(
      <PlayerBar
        color={COLOR_WHITE}
        position="top"
        playersInfo={[{ color: COLOR_WHITE, username: 'alice', is_anonymous: false }]}
        timer={{ белый: 120, черный: 90 }}
        moversColor={COLOR_WHITE}
        myColor={COLOR_WHITE}
        timeControl={300}
        countsByType={{ white: { batyr: 2, shatra: 7 }, black: { batyr: 2, shatra: 7 } }}
      />,
    );

    const bar = container.querySelector('.game-player-bar--mobile');
    expect(bar).toBeTruthy();
    expect(bar.querySelector('.game-player-bar__info')).toBeTruthy();
    expect(screen.getByText('alice')).toBeTruthy();
    expect(screen.getByText('2')).toBeTruthy();
    expect(screen.getByText('7')).toBeTruthy();
    expect(screen.getByText('2:00')).toBeTruthy();
    expect(bar.querySelector('.game-player-bar__time')).toBeTruthy();
    expect(bar.querySelector('.room-counts-row--inline')).toBeTruthy();
  });
});
