import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { fireEvent, render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LiteUiProvider } from '../context/LiteUiContext';
import AuthNav from './AuthNav';
import { LITE_UI_KEY } from '../ui/liteUiSettings';

const matchMediaMock = vi.fn();

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    isAuthenticated: false,
    loading: false,
    logout: vi.fn(),
  }),
}));

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => key,
    i18n: { language: 'ru', changeLanguage: vi.fn() },
  }),
}));

vi.mock('./LocaleSwitcher', () => ({
  default: () => <div data-testid="locale-switcher" />,
}));

vi.mock('./HomeTab', () => ({
  default: () => <a href="/">nav.home</a>,
}));

vi.mock('./TutorialTab', () => ({
  default: () => <a href="/tutorial">nav.tutorial</a>,
}));

function renderNav(pathname) {
  return render(
    <MemoryRouter initialEntries={[pathname]}>
      <LiteUiProvider>
        <AuthNav />
      </LiteUiProvider>
    </MemoryRouter>,
  );
}

describe('AuthNav compact mobile nav', () => {
  beforeEach(() => {
    localStorage.removeItem(LITE_UI_KEY);
    matchMediaMock.mockImplementation((query) => ({
      matches: query.includes('1319px'),
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    window.matchMedia = matchMediaMock;
    document.documentElement.classList.remove('app-shell--game-nav-compact');
  });

  afterEach(() => {
    cleanup();
    localStorage.removeItem(LITE_UI_KEY);
    document.documentElement.classList.remove('app-shell--game-nav-compact');
  });

  it('shows hamburger without support button on game route in mobile layout', () => {
    renderNav('/room123');
    expect(screen.getByRole('button', { name: 'nav.openMenu' })).toBeTruthy();
    expect(screen.queryByRole('link', { name: 'nav.support' })).toBeNull();
    expect(document.querySelector('.app-top-center')).toBeNull();
    expect(document.querySelector('.app-top-start--compact')?.querySelector('.app-support-btn')).toBeNull();
    expect(screen.queryByText('nav.home')).toBeNull();
    expect(screen.queryByText('lobby.title')).toBeNull();
    expect(document.documentElement.classList.contains('app-shell--game-nav-compact')).toBe(true);
  });

  it('does not show support button in AuthNav on lobby mobile (rendered in Lobby)', () => {
    renderNav('/');
    expect(screen.queryByRole('link', { name: 'nav.support' })).toBeNull();
    expect(document.querySelector('.app-top-center--lobby-mobile')).toBeNull();
  });

  it('does not show support button in mobile drawer', () => {
    renderNav('/room123');
    fireEvent.click(screen.getByRole('button', { name: 'nav.openMenu' }));
    const drawer = document.getElementById('app-nav-drawer');
    expect(drawer.querySelector('a[href*="cloudtips"]')).toBeNull();
  });

  it('shows home and tutorial in drawer on mobile', () => {
    renderNav('/room123');
    fireEvent.click(screen.getByRole('button', { name: 'nav.openMenu' }));
    expect(screen.getByText('nav.home')).toBeTruthy();
    expect(screen.getByText('nav.tutorial')).toBeTruthy();
    expect(screen.getByText('lobby.title')).toBeTruthy();
  });

  it('shows full nav on desktop layout', () => {
    matchMediaMock.mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    renderNav('/');
    expect(screen.queryByRole('button', { name: 'nav.openMenu' })).toBeNull();
    expect(screen.getByText('lobby.title')).toBeTruthy();
    expect(screen.getByText('nav.home')).toBeTruthy();
    expect(screen.getByText('nav.tutorial')).toBeTruthy();
    expect(screen.getByRole('link', { name: 'nav.support' })).toBeTruthy();
    expect(document.querySelector('.app-top-center')).toBeNull();
    expect(document.querySelector('.app-chrome-nav-tabs .app-support-btn')).toBeNull();
    expect(document.querySelector('.app-top-start > .app-support-btn')).toBeTruthy();
  });

  it('does not show lite board toggle on lobby', () => {
    matchMediaMock.mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    renderNav('/');
    expect(screen.queryByRole('button', { name: 'nav.liteUiOff' })).toBeNull();
  });

  it('toggles lite board from desktop top bar in game', () => {
    matchMediaMock.mockImplementation((query) => ({
      matches: false,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
    renderNav('/room123');
    const btn = screen.getByRole('button', { name: 'nav.liteUiOff' });
    expect(btn.getAttribute('aria-pressed')).toBe('false');
    fireEvent.click(btn);
    expect(localStorage.getItem(LITE_UI_KEY)).toBe('true');
    expect(screen.getByRole('button', { name: 'nav.liteUiOn' }).getAttribute('aria-pressed')).toBe('true');
  });
});
