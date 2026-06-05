import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import GameViewport from './GameViewport';

vi.mock('../../BoardGrid', () => ({
  default: () => <div data-testid="board-grid" />,
}));

vi.mock('../MoveHistory', () => ({
  default: () => <div data-testid="move-history" />,
}));

vi.mock('../PlayerBar', () => ({
  default: () => <div data-testid="player-bar" />,
}));

describe('GameViewport', () => {
  afterEach(() => {
    cleanup();
  });

  const baseState = {
    board: [],
    playersInfo: [],
    timer: {},
    moversColor: null,
    myColor: 'белый',
    timeControl: null,
    countsByType: {},
    moveFrom: null,
    highlightedEssential: [],
    highlightedCaptured: [],
    lastMove: null,
    historyFrom: null,
    historyTo: null,
    aiThinking: false,
    opponentDisconnected: true,
    disconnectCountdown: 30,
  };

  it('does not render full-board overlay when opponent disconnected', () => {
    const { container } = render(
      <GameViewport
        boardTop="белый"
        boardBottom="черный"
        state={baseState}
        isBoardBlocked
        onCellClick={vi.fn()}
        actionsBar={null}
        moveHistoryProps={{}}
      />,
    );
    expect(container.querySelector('.opponent-disconnected-overlay')).toBeNull();
    expect(container.querySelector('.opponent-disconnect-status--board-edge')).toBeTruthy();
    expect(container.querySelector('.game-viewport-column')).toBeTruthy();
    expect(container.querySelector('.game-viewport-fold')).toBeTruthy();
    expect(container.querySelector('.game-viewport-below-fold')).toBeTruthy();
    expect(container.querySelector('.game-viewport-actions')).toBeNull();
    expect(container.querySelector('.game-viewport-below-fold')?.closest('.game-viewport-first')).toBeNull();
  });
});
