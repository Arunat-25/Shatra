import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function HomeTab({ onNavigate }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const isActive = pathname === '/';

  return (
    <NavLink
      to="/"
      className={`tutorial-tab${isActive ? ' is-active' : ''}`}
      aria-label={t('nav.home')}
      title={t('nav.home')}
      onClick={onNavigate}
      end
    >
      {t('nav.home')}
    </NavLink>
  );
}
