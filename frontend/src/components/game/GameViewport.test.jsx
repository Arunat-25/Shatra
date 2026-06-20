import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { LiteUiProvider } from '../../context/LiteUiContext';
import { setLiteUiEnabled, LITE_UI_KEY } from '../../ui/liteUiSettings';
import GameViewport from './GameViewport';

vi.mock('../BoardSurface', () => ({
  default: () => <div data-testid="board-surface" />,
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
    localStorage.removeItem(LITE_UI_KEY);
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
      <LiteUiProvider>
        <GameViewport
          boardTop="белый"
          boardBottom="черный"
          state={baseState}
          isBoardBlocked
          onCellClick={vi.fn()}
          actionsBar={null}
          moveHistoryProps={{}}
        />
      </LiteUiProvider>,
    );
    expect(container.querySelector('.opponent-disconnected-overlay')).toBeNull();
    expect(container.querySelector('.opponent-disconnect-status--board-edge')).toBeTruthy();
    expect(container.querySelector('.game-viewport-column')).toBeTruthy();
    expect(container.querySelector('.game-viewport-fold')).toBeTruthy();
    expect(container.querySelector('.game-viewport-below-fold')).toBeTruthy();
    expect(container.querySelector('.game-viewport-actions')).toBeNull();
    expect(container.querySelector('.game-viewport-below-fold')?.closest('.game-viewport-first')).toBeNull();
  });

  it('does not dim board in lite mode while AI thinks', () => {
    setLiteUiEnabled(true);
    const { container } = render(
      <LiteUiProvider>
        <GameViewport
          boardTop="белый"
          boardBottom="черный"
          state={{ ...baseState, aiThinking: true, opponentDisconnected: false }}
          isBoardBlocked
          onCellClick={vi.fn()}
          actionsBar={null}
          moveHistoryProps={{}}
        />
      </LiteUiProvider>,
    );
    const board = container.querySelector('.board');
    expect(board?.classList.contains('board--lite')).toBe(true);
    expect(board?.classList.contains('board-dimmed')).toBe(false);
    expect(board?.classList.contains('board-ai-thinking')).toBe(false);
  });

  it('dims board in regular mode while AI thinks', () => {
    setLiteUiEnabled(false);
    const { container } = render(
      <LiteUiProvider>
        <GameViewport
          boardTop="белый"
          boardBottom="черный"
          state={{ ...baseState, aiThinking: true, opponentDisconnected: false }}
          isBoardBlocked
          onCellClick={vi.fn()}
          actionsBar={null}
          moveHistoryProps={{}}
        />
      </LiteUiProvider>,
    );
    const board = container.querySelector('.board');
    expect(board?.classList.contains('board-dimmed')).toBe(true);
    expect(board?.classList.contains('board-ai-thinking')).toBe(true);
  });
});
