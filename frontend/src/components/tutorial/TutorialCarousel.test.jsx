import React from 'react';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TutorialCarousel from './TutorialCarousel';

vi.mock('./slides/MainFieldSlide', () => ({
  default: () => <div data-testid="slide-main">main</div>,
}));
vi.mock('./slides/FortressSlide', () => ({
  default: () => <div data-testid="slide-fortress">fortress</div>,
}));
vi.mock('./slides/GateSlide', () => ({
  default: () => <div data-testid="slide-gate">gate</div>,
}));
vi.mock('./slides/PiecesIntroSlide', () => ({
  default: () => <div data-testid="slide-pieces">pieces</div>,
}));

describe('TutorialCarousel', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders first slide and title', () => {
    render(<TutorialCarousel />);
    expect(screen.getByRole('heading', { name: /правила|rules/i })).toBeTruthy();
    expect(screen.getByTestId('slide-main')).toBeTruthy();
  });

  it('advances slides on viewport click', () => {
    render(<TutorialCarousel />);
    const viewport = document.querySelector('.tutorial-carousel__viewport');
    fireEvent.click(viewport);
    expect(screen.getByTestId('slide-fortress')).toBeTruthy();
    fireEvent.click(viewport);
    expect(screen.getByTestId('slide-gate')).toBeTruthy();
    fireEvent.click(viewport);
    expect(screen.getByTestId('slide-pieces')).toBeTruthy();
  });

  it('has four dot indicators', () => {
    const { container } = render(<TutorialCarousel />);
    const dots = container.querySelectorAll('.tutorial-carousel__dots .tutorial-carousel__dot');
    expect(dots).toHaveLength(4);
  });
});
