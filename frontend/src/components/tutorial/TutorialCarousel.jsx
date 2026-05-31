import React from 'react';
import { useTranslation } from 'react-i18next';
import useTutorialCarousel, { TUTORIAL_SLIDE_COUNT } from '../../hooks/useTutorialCarousel';
import MainFieldSlide from './slides/MainFieldSlide';
import FortressSlide from './slides/FortressSlide';
import GateSlide from './slides/GateSlide';
import PiecesIntroSlide from './slides/PiecesIntroSlide';

const SLIDES = [MainFieldSlide, FortressSlide, GateSlide, PiecesIntroSlide];

export default function TutorialCarousel() {
  const { t } = useTranslation();
  const {
    index,
    goTo,
    onPointerDown,
    onPointerUp,
    onPointerCancel,
    onPointerLeave,
    onClick,
  } = useTutorialCarousel(TUTORIAL_SLIDE_COUNT);

  const Slide = SLIDES[index];

  return (
    <aside className="lobby-tutorial" aria-labelledby="tutorial-heading">
      <h2 id="tutorial-heading" className="lobby-tutorial__title">
        {t('tutorial.title')}
      </h2>

      <div
        className="tutorial-carousel"
        role="region"
        aria-roledescription="carousel"
        aria-label={t('tutorial.title')}
      >
        <div
          className="tutorial-carousel__viewport"
          onClick={onClick}
          onPointerDown={onPointerDown}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerCancel}
          onPointerLeave={onPointerLeave}
        >
          <div className="tutorial-carousel__slide" aria-live="polite">
            <Slide />
          </div>
        </div>

        <div className="tutorial-carousel__dots" role="tablist" aria-label={t('tutorial.title')}>
          {SLIDES.map((_, i) => (
            <button
              key={i}
              type="button"
              role="tab"
              className="tutorial-carousel__dot"
              aria-selected={i === index}
              aria-current={i === index ? 'true' : undefined}
              aria-label={`${t('tutorial.title')} ${i + 1}/${SLIDES.length}`}
              onClick={(e) => {
                e.stopPropagation();
                goTo(i);
              }}
            />
          ))}
        </div>
      </div>
    </aside>
  );
}
