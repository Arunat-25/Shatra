import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { LiteUiProvider } from '../context/LiteUiContext';
import BoardSurface from './BoardSurface';
import useMediaQuery from '../hooks/useMediaQuery';
import { setLiteUiEnabled, LITE_UI_KEY } from '../ui/liteUiSettings';

vi.mock('../hooks/useMediaQuery');

let lastBoardGridProps = null;
let lastCanvasProps = null;

vi.mock('../BoardGrid', () => ({
  default: (props) => {
    lastBoardGridProps = props;
    return <div data-testid="board-grid" />;
  },
}));

vi.mock('../board/CanvasBoard', () => ({
  default: (props) => {
    lastCanvasProps = props;
    return <div data-testid="board-canvas" />;
  },
}));

vi.mock('../board/pieceSprites', () => ({
  preloadPieceSprites: vi.fn(() => Promise.resolve()),
}));

function renderSurface(litePref = false) {
  setLiteUiEnabled(litePref);
  return render(
    <LiteUiProvider>
      <BoardSurface board={{}} onCellClick={() => {}} myColor="белый" enablePieceDrag />
    </LiteUiProvider>,
  );
}

describe('BoardSurface', () => {
  beforeEach(() => {
    localStorage.removeItem(LITE_UI_KEY);
    lastBoardGridProps = null;
    lastCanvasProps = null;
    vi.mocked(useMediaQuery).mockReturnValue(false);
  });

  afterEach(() => {
    cleanup();
  });

  it('uses full DOM board on desktop when lite UI is off', () => {
    renderSurface(false);
    expect(lastCanvasProps).toBeNull();
    expect(lastBoardGridProps).not.toBeNull();
    expect(lastBoardGridProps.pieceVariant).toBeUndefined();
    expect(lastBoardGridProps.enablePieceDrag).toBe(true);
  });

  it('uses canvas board when lite UI is on', () => {
    renderSurface(true);
    expect(lastCanvasProps).not.toBeNull();
    expect(lastCanvasProps.drawTheme).toBe('lite');
    expect(lastCanvasProps.vectorOnlySprites).toBe(true);
    expect(lastBoardGridProps).toBeNull();
  });

  it('uses lite DOM pieces without drag on compact viewport when lite is off', () => {
    vi.mocked(useMediaQuery).mockReturnValue(true);
    renderSurface(false);
    expect(lastCanvasProps).toBeNull();
    expect(lastBoardGridProps.pieceVariant).toBe('lite');
    expect(lastBoardGridProps.enablePieceDrag).toBe(false);
  });
});
