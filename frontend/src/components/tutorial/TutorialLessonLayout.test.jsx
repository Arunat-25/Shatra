import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { LiteUiProvider } from '../../context/LiteUiContext';
import TutorialLessonLayout from './TutorialLessonLayout';
import useMediaQuery from '../../hooks/useMediaQuery';
import { setLiteUiEnabled, LITE_UI_KEY } from '../../ui/liteUiSettings';

vi.mock('../../hooks/useMediaQuery');
vi.mock('../../debug/tutorialLayoutProbe', () => ({
  probeTutorialLayout: vi.fn(),
}));
vi.mock('../../hooks/useDevLayoutProbe', () => ({
  default: vi.fn(),
}));

let lastBoardSurfaceProps = null;

vi.mock('../BoardSurface', () => ({
  default: (props) => {
    lastBoardSurfaceProps = props;
    return <div data-testid="board-surface" />;
  },
}));

function renderLayout(props = {}) {
  return render(
    <LiteUiProvider>
      <TutorialLessonLayout
        board={{ 10: 'белый бий' }}
        text="Test lesson text"
        onNext={() => {}}
        onBack={() => {}}
        canProceed
        {...props}
      />
    </LiteUiProvider>,
  );
}

describe('TutorialLessonLayout', () => {
  beforeEach(() => {
    localStorage.removeItem(LITE_UI_KEY);
    lastBoardSurfaceProps = null;
    vi.mocked(useMediaQuery).mockReturnValue(false);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('renders BoardSurface with tutorial props', () => {
    renderLayout({
      tutorialDimmedCells: [1, 2],
      highlightedEssential: [10],
      interactive: true,
      onCellClick: () => {},
    });

    expect(screen.getByTestId('board-surface')).toBeTruthy();
    expect(lastBoardSurfaceProps.tutorialDimmedCells).toEqual([1, 2]);
    expect(lastBoardSurfaceProps.highlightedEssential).toEqual([10]);
    expect(lastBoardSurfaceProps.enablePieceDrag).toBe(false);
    expect(lastBoardSurfaceProps.interactive).toBe(true);
  });

  it('adds board--lite class when lite UI is enabled', () => {
    setLiteUiEnabled(true);
    const { container } = renderLayout();
    expect(container.querySelector('.board.board--lite')).toBeTruthy();
  });

  it('marks board disabled when not interactive', () => {
    const { container } = renderLayout({ interactive: false });
    expect(container.querySelector('.board.disabled')).toBeTruthy();
  });
});
