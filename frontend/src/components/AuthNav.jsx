import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import useAuthNavOffset from '../hooks/useAuthNavOffset';
import useEscapeKey from '../hooks/useEscapeKey';
import useMediaQuery from '../hooks/useMediaQuery';
import LocaleSwitcher from './LocaleSwitcher';
import HomeTab from './HomeTab';
import TutorialTab from './TutorialTab';
import BugReportModal from './BugReportModal';
import SupportButton from './SupportButton';
import LiteUiToggle from './LiteUiToggle';
import { COMPACT_GAME_QUERY } from '../constants';
import { isGamePath } from '../appPaths';

function IconProfile() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function IconLogout() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

function IconMenu() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <line x1="4" y1="12" x2="20" y2="12" />
    </svg>
  );
}

export default function AuthNav() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const { user, isAuthenticated, loading, logout } = useAuth();
  const topStartRef = useRef(null);
  const topEndRef = useRef(null);
  const menuToggleRef = useRef(null);
  const isMobileLayout = useMediaQuery(COMPACT_GAME_QUERY);
  const compactMobileNav = isMobileLayout;
  const showLiteBoardToggle = isGamePath(pathname);
  const [menuOpen, setMenuOpen] = useState(false);
  const [bugReportOpen, setBugReportOpen] = useState(false);

  const closeMenu = useCallback(() => setMenuOpen(false), []);
  useEscapeKey(menuOpen, closeMenu);

  useEffect(() => {
    document.documentElement.classList.toggle('app-shell--game-nav-compact', compactMobileNav);
    return () => document.documentElement.classList.remove('app-shell--game-nav-compact');
  }, [compactMobileNav]);

  useEffect(() => {
    if (!compactMobileNav) setMenuOpen(false);
  }, [compactMobileNav, pathname]);

  const onLobbyPage = pathname === '/';

  const navRef = useAuthNavOffset(
    [loading, isAuthenticated, pathname, user?.username, compactMobileNav, menuOpen, onLobbyPage],
    topStartRef,
    topEndRef,
    menuToggleRef,
    compactMobileNav,
    null,
    onLobbyPage,
  );
  const onLoginPage = pathname === '/login';
  const onRegisterPage = pathname === '/register';
  const onProfilePage = pathname === '/profile';
  const onAdminPage = pathname === '/admin';
  const handleLogout = () => {
    closeMenu();
    logout();
  };

  const openBugReport = () => {
    closeMenu();
    setBugReportOpen(true);
  };

  const accountNav = (inDrawer = false) => (
    <nav
      ref={inDrawer ? null : navRef}
      className={`app-auth-nav${inDrawer ? ' app-auth-nav--drawer' : ''}`}
      aria-label={t('nav.account')}
    >
      {loading ? (
        <span className="app-auth-nav__placeholder" aria-hidden />
      ) : isAuthenticated ? (
        <>
          <span className="app-auth-nav__username" title={user.username}>
            {user.username}
          </span>
          {!onProfilePage && (
            <Link
              to="/profile"
              className="app-auth-nav__icon-btn"
              aria-label={t('nav.profile')}
              title={t('nav.profile')}
              onClick={inDrawer ? closeMenu : undefined}
            >
              <IconProfile />
            </Link>
          )}
          {user.is_admin && !onAdminPage && (
            <Link to="/admin" className="app-auth-nav__link" onClick={inDrawer ? closeMenu : undefined}>
              {t('nav.admin')}
            </Link>
          )}
          <button
            type="button"
            className="app-auth-nav__icon-btn"
            onClick={inDrawer ? handleLogout : () => logout()}
            aria-label={t('nav.logout')}
            title={t('nav.logout')}
          >
            <IconLogout />
          </button>
        </>
      ) : (
        <>
          {!onLoginPage && (
            <Link to="/login" className="app-auth-nav__link" onClick={inDrawer ? closeMenu : undefined}>
              {t('nav.login')}
            </Link>
          )}
          {!onRegisterPage && (
            <Link
              to="/register"
              className="app-auth-nav__link app-auth-nav__link--primary"
              onClick={inDrawer ? closeMenu : undefined}
            >
              {t('nav.register')}
            </Link>
          )}
        </>
      )}
    </nav>
  );

  const topTools = compactMobileNav ? (
    <div ref={topStartRef} className="app-top-start app-top-start--compact">
      <button
        ref={menuToggleRef}
        type="button"
        className="app-nav-menu-toggle"
        aria-expanded={menuOpen}
        aria-controls="app-nav-drawer"
        aria-label={menuOpen ? t('nav.closeMenu') : t('nav.openMenu')}
        onClick={() => setMenuOpen((open) => !open)}
      >
        <IconMenu />
      </button>
      {showLiteBoardToggle ? <LiteUiToggle /> : null}
    </div>
  ) : (
    <div ref={topStartRef} className="app-top-start">
      <Link to="/" className="app-brand" aria-label={t('nav.home')}>
        {t('lobby.title')}
      </Link>
      <div className="app-chrome-nav-tabs">
        <HomeTab />
        <TutorialTab />
      </div>
      <SupportButton />
    </div>
  );

  const drawer = compactMobileNav && menuOpen ? (
    <div className="app-nav-drawer-backdrop" onClick={closeMenu} role="presentation">
      <nav
        id="app-nav-drawer"
        className="app-nav-drawer"
        aria-label={t('nav.openMenu')}
        onClick={(e) => e.stopPropagation()}
      >
        <Link to="/" className="app-nav-drawer__brand" onClick={closeMenu}>
          {t('lobby.title')}
        </Link>
        <div className="app-nav-drawer__section">
          <HomeTab onNavigate={closeMenu} />
        </div>
        <div className="app-nav-drawer__section">
          <TutorialTab onNavigate={closeMenu} />
        </div>
        <div className="app-nav-drawer__section">
          <button type="button" className="app-nav-drawer__link" onClick={openBugReport}>
            {t('nav.reportBug')}
          </button>
        </div>
        <div className="app-nav-drawer__section app-nav-drawer__section--locale">
          <LocaleSwitcher />
        </div>
        <div className="app-nav-drawer__section app-nav-drawer__section--account">
          {accountNav(true)}
        </div>
      </nav>
    </div>
  ) : null;

  return (
    <>
      {topTools}
      {!compactMobileNav && (
        <div ref={topEndRef} className="app-top-end">
          {showLiteBoardToggle ? (
            <div className="app-lite-board-nav">
              <LiteUiToggle />
            </div>
          ) : null}
          <div className="app-auth-nav">
            <button
              type="button"
              className="app-auth-nav__link"
              onClick={() => setBugReportOpen(true)}
            >
              {t('nav.reportBug')}
            </button>
          </div>
          <div className="app-locale-nav">
            <LocaleSwitcher />
          </div>
          {accountNav(false)}
        </div>
      )}
      {drawer}
      <BugReportModal open={bugReportOpen} onClose={() => setBugReportOpen(false)} />
    </>
  );
}
