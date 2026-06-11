import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import SupportButton from './SupportButton';
import { SUPPORT_URL } from '../config/support';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => (key === 'nav.support' ? 'Поддержать' : key),
  }),
}));

describe('SupportButton', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders external link with support URL and label', () => {
    render(<SupportButton />);
    const link = screen.getByRole('link', { name: 'Поддержать' });
    expect(link.getAttribute('href')).toBe(SUPPORT_URL);
    expect(link.getAttribute('target')).toBe('_blank');
    expect(link.getAttribute('rel')).toBe('noopener noreferrer');
    expect(link.textContent).toContain('Поддержать');
  });

  it('applies compact modifier class', () => {
    render(<SupportButton compact />);
    const link = screen.getByRole('link', { name: 'Поддержать' });
    expect(link.className).toContain('app-support-btn--compact');
  });
});
