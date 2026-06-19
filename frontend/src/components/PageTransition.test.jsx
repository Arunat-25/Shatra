import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PageTransition from './PageTransition';
import useMediaQuery from '../hooks/useMediaQuery';

vi.mock('../hooks/useMediaQuery');

function renderTransition() {
  return render(
    <MemoryRouter>
      <PageTransition>
        <div data-testid="child">content</div>
      </PageTransition>
    </MemoryRouter>,
  );
}

describe('PageTransition', () => {
  beforeEach(() => {
    vi.mocked(useMediaQuery).mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
  });

  it('uses animated transition on desktop layout', () => {
    const { container } = renderTransition();
    const wrapper = container.querySelector('.page-transition');
    expect(wrapper?.style.transition).toContain('opacity');
    expect(wrapper?.style.transform).toBeTruthy();
  });

  it('skips animated transition on compact layout', () => {
    vi.mocked(useMediaQuery).mockReturnValue(true);
    const { container } = renderTransition();
    const wrapper = container.querySelector('.page-transition');
    expect(wrapper?.style.transition).toBe('');
    expect(wrapper?.style.opacity).toBe('');
    expect(wrapper?.style.transform).toBe('');
  });
});
