import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import LobbyChat from './LobbyChat';

const mockUseLobbyChat = vi.fn();

vi.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key) => key }),
}));

vi.mock('../hooks/useLobbyChat', () => ({
  default: (...args) => mockUseLobbyChat(...args),
}));

describe('LobbyChat', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders lobby chat panel with 500-char input', () => {
    mockUseLobbyChat.mockReturnValue({
      messages: [],
      send: vi.fn(),
      error: '',
      disabled: false,
      clearError: vi.fn(),
    });
    render(<LobbyChat />);
    expect(screen.getByRole('textbox').getAttribute('maxLength')).toBe('500');
    expect(screen.getByPlaceholderText('lobbyChat.placeholder')).toBeTruthy();
    expect(screen.getByText('lobbyChat.cooldownHint').textContent).toContain('lobbyChat.cooldownHint');
  });

  it('shows error alert and dismiss clears it', () => {
    const clearError = vi.fn();
    mockUseLobbyChat.mockReturnValue({
      messages: [],
      send: vi.fn(),
      error: 'Too fast',
      disabled: false,
      clearError,
    });
    render(<LobbyChat />);
    expect(screen.getByRole('alert').textContent).toContain('Too fast');
    fireEvent.click(screen.getByRole('button', { name: 'lobby.closeError' }));
    expect(clearError).toHaveBeenCalled();
  });

  it('disables input when hook reports disconnected', () => {
    mockUseLobbyChat.mockReturnValue({
      messages: [],
      send: vi.fn(),
      error: '',
      disabled: true,
      clearError: vi.fn(),
    });
    render(<LobbyChat />);
    expect(screen.getByRole('textbox').disabled).toBe(true);
  });
});
