import React from 'react';
import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import LocaleSwitcher from './LocaleSwitcher';
import { LOCALE_ARIA } from './LocaleFlag';

const changeLanguage = vi.fn();

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    i18n: { language: 'ru', changeLanguage },
  }),
}));

vi.mock('../i18n', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getStoredLocale: () => 'ru',
    setStoredLocale: vi.fn(),
    normalizeLocale: (lng) => (lng === 'alt' ? 'ru' : lng || 'ru'),
  };
});

vi.mock('./LocaleFlag', () => ({
  default: ({ locale }) => <span data-testid={`flag-${locale}`} />,
  LOCALE_ARIA: {
    ru: 'Русский',
    en: 'English',
    alt: 'Алтайский',
  },
}));

describe('LocaleSwitcher', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders only ru and en buttons, not alt', () => {
    render(<LocaleSwitcher />);
    expect(screen.getByRole('button', { name: LOCALE_ARIA.ru })).toBeTruthy();
    expect(screen.getByRole('button', { name: LOCALE_ARIA.en })).toBeTruthy();
    expect(screen.queryByRole('button', { name: LOCALE_ARIA.alt })).toBeNull();
    expect(screen.getAllByRole('button')).toHaveLength(2);
  });
});
