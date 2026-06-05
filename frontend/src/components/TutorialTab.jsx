import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { isTutorialPath } from '../tutorialPaths';

export default function TutorialTab({ onNavigate }) {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const isActive = isTutorialPath(pathname);

  return (
    <NavLink
      to="/tutorial"
      className={`tutorial-tab${isActive ? ' is-active' : ''}`}
      aria-label={t('nav.tutorial')}
      title={t('nav.tutorial')}
      onClick={onNavigate}
    >
      {t('nav.tutorial')}
    </NavLink>
  );
}
