import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import RatingGainBlockedNotice from './RatingGainBlockedNotice';

const mockUseAuth = vi.fn(() => ({ user: null }));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('RatingGainBlockedNotice', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ user: null });
  });

  afterEach(() => {
    cleanup();
  });

  it('renders nothing when user is not blocked', () => {
    const { container } = render(<RatingGainBlockedNotice />);
    expect(container.firstChild).toBeNull();
  });

  it('shows warning when rating_gain_blocked_until is in the future', () => {
    mockUseAuth.mockReturnValue({
      user: {
        rating_gain_blocked_until: new Date(Date.now() + 3600_000).toISOString(),
      },
    });
    render(<RatingGainBlockedNotice />);
    expect(document.querySelector('.lobby-rating-blocked')).toBeTruthy();
  });
});
