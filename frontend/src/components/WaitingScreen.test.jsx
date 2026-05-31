import React from 'react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import WaitingScreen from './WaitingScreen';

vi.mock('qrcode', () => ({
  default: {
    toDataURL: vi.fn(() => Promise.resolve('data:image/png;base64,qr')),
  },
}));

describe('WaitingScreen QR', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders QR when showInviteLink is true', async () => {
    render(
      <WaitingScreen roomId="abc12345" showInviteLink modeAi={false} />,
    );
    const img = await screen.findByAltText(/qr|приглаш/i);
    expect(img.getAttribute('src')).toBe('data:image/png;base64,qr');
  });

  it('does not render invite QR when waiting for opponent', () => {
    render(
      <WaitingScreen
        roomId="abc12345"
        showInviteLink={false}
        modeAi={false}
      />,
    );
    expect(screen.queryByAltText(/qr|приглаш/i)).toBeNull();
    expect(screen.getByText(/ожидание|waiting/i)).toBeTruthy();
  });
});
