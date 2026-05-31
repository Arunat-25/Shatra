import React from 'react';
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import OpponentDisconnectStatus from './OpponentDisconnectStatus';

describe('OpponentDisconnectStatus', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders title, text and countdown', () => {
    render(
      <OpponentDisconnectStatus disconnectCountdown={25} placement="sidebar" />,
    );
    expect(screen.getByRole('status')).toBeTruthy();
    expect(screen.getByText(/соперник отключился|opponent disconnected/i)).toBeTruthy();
    expect(screen.getByText('25')).toBeTruthy();
  });

  it('applies placement modifier class', () => {
    const { container } = render(
      <OpponentDisconnectStatus disconnectCountdown={10} placement="board-edge" />,
    );
    expect(container.querySelector('.opponent-disconnect-status--board-edge')).toBeTruthy();
  });
});
