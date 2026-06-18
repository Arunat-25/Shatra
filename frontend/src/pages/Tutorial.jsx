import '../styles/tutorial.css';
import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { probeTutorialLayout } from '../debug/tutorialLayoutProbe';

const SECTION_IDS = [1, 2, 3, 4, 5];

export default function Tutorial() {
  const { t } = useTranslation();

  useEffect(() => {
    const run = () => probeTutorialLayout('tutorial-index');
    run();
    const tId = window.setTimeout(run, 150);
    window.addEventListener('resize', run);
    return () => {
      window.clearTimeout(tId);
      window.removeEventListener('resize', run);
    };
  }, []);

  return (
    <div className="tutorial-page">
      <div className="tutorial-page__inner">
        <h1>{t('tutorial.pageTitle')}</h1>
        <ul className="tutorial-sections">
          {SECTION_IDS.map((id) => {
            const label = t(`tutorial.section${id}.label`);
            const title = t(`tutorial.section${id}.title`);
            const body = (
              <>
                <span className="tutorial-section-card__label">{label}</span>
                <span className="tutorial-section-card__title">{title}</span>
              </>
            );
            return (
              <li key={id}>
                {id === 1 || id === 2 || id === 3 || id === 4 || id === 5 ? (
                  <Link to={`/tutorial/${id}`} className="tutorial-section-card">
                    {body}
                  </Link>
                ) : (
                  <button type="button" className="tutorial-section-card">
                    {body}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
