import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import LocaleSwitcher from './LocaleSwitcher';

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

export default function AuthNav() {
  const { pathname } = useLocation();
  const { t } = useTranslation();
  const { user, isAuthenticated, loading, logout } = useAuth();
  const onLoginPage = pathname === '/login';
  const onRegisterPage = pathname === '/register';
  const onProfilePage = pathname === '/profile';

  if (loading) {
    return (
      <nav className="app-auth-nav" aria-label={t('nav.account')}>
        <span className="app-auth-nav__placeholder" aria-hidden />
      </nav>
    );
  }

  return (
    <nav className="app-auth-nav" aria-label={t('nav.account')}>
      <LocaleSwitcher />
      {isAuthenticated ? (
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
            >
              <IconProfile />
            </Link>
          )}
          <button
            type="button"
            className="app-auth-nav__icon-btn"
            onClick={() => logout()}
            aria-label={t('nav.logout')}
            title={t('nav.logout')}
          >
            <IconLogout />
          </button>
        </>
      ) : (
        <>
          {!onLoginPage && (
            <Link to="/login" className="app-auth-nav__link">
              {t('nav.login')}
            </Link>
          )}
          {!onRegisterPage && (
            <Link to="/register" className="app-auth-nav__link app-auth-nav__link--primary">
              {t('nav.register')}
            </Link>
          )}
        </>
      )}
    </nav>
  );
}
