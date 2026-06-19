import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LiteUiProvider } from '../context/LiteUiContext';
import PageTransition from './PageTransition';
import useMediaQuery from '../hooks/useMediaQuery';
import { setLiteUiEnabled, LITE_UI_KEY } from '../ui/liteUiSettings';

vi.mock('../hooks/useMediaQuery');

function renderTransition(litePref = false) {
  setLiteUiEnabled(litePref);
  return render(
    <MemoryRouter>
      <LiteUiProvider>
        <PageTransition>
          <div data-testid="child">content</div>
        </PageTransition>
      </LiteUiProvider>
    </MemoryRouter>,
  );
}

describe('PageTransition', () => {
  beforeEach(() => {
    localStorage.removeItem(LITE_UI_KEY);
    vi.mocked(useMediaQuery).mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
    document.documentElement.classList.remove('app-shell--lite-ui');
  });

  it('uses animated transition on desktop when lite UI is off', () => {
    const { container } = renderTransition(false);
    const wrapper = container.querySelector('.page-transition');
    expect(wrapper?.style.transition).toContain('opacity');
    expect(wrapper?.style.transform).toBeTruthy();
  });

  it('skips animated transition on desktop when lite UI is on', () => {
    const { container } = renderTransition(true);
    const wrapper = container.querySelector('.page-transition');
    expect(wrapper?.style.transition).toBe('');
    expect(wrapper?.style.opacity).toBe('');
    expect(wrapper?.style.transform).toBe('');
  });
});
