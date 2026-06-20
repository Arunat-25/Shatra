import { readBoardLayoutSnapshot } from '../board/boardLayoutGeometry';
import { sendDevProbe } from './devProbe';

function rect(el) {
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {
    h: Math.round(r.height),
    w: Math.round(r.width),
    top: Math.round(r.top),
    bottom: Math.round(r.bottom),
  };
}

function cs(el, prop) {
  return el ? getComputedStyle(el).getPropertyValue(prop) : null;
}

/** Debug probe: tutorial page layout (overflow, board units). Dev only. */
export function probeTutorialLayout(tag, extra = {}) {
  const shell = document.querySelector('.app-shell');
  const appMain = document.querySelector('.app-main');
  const pageTransition = document.querySelector('.page-transition');
  const lesson = document.querySelector('.tutorial-lesson');
  const stage = document.querySelector('.tutorial-lesson__stage');
  const board = document.querySelector('.tutorial-lesson .board');
  const panel = document.querySelector('.tutorial-lesson__panel');
  const tutorialPage = document.querySelector('.tutorial-page');
  const sampleCell = document.querySelector('.tutorial-lesson .field-of-king .kletka');
  const sampleRow = document.querySelector('.tutorial-lesson .field-of-king .row');
  const layoutSnapshot = readBoardLayoutSnapshot(document);
  const boardCs = board ? getComputedStyle(board) : null;
  const cellCs = sampleCell ? getComputedStyle(sampleCell) : null;

  const data = {
    tag,
    path: window.location.pathname,
    viewport: { w: window.innerWidth, h: window.innerHeight },
    scroll: {
      windowY: window.scrollY,
      htmlTop: document.documentElement.scrollTop,
      bodyTop: document.body.scrollTop,
      htmlSH: document.documentElement.scrollHeight,
      bodySH: document.body.scrollHeight,
    },
    shellClass: shell?.className ?? null,
    html: {
      height: cs(document.documentElement, 'height'),
      overflowY: cs(document.documentElement, 'overflow-y'),
    },
    body: {
      height: cs(document.body, 'height'),
      overflowY: cs(document.body, 'overflow-y'),
    },
    root: {
      height: cs(document.getElementById('root'), 'height'),
      padding: cs(document.getElementById('root'), 'padding'),
    },
    shell: rect(shell),
    appMain: {
      ...rect(appMain),
      heightCs: cs(appMain, 'height'),
      flex: cs(appMain, 'flex'),
    },
    pageTransition: {
      ...rect(pageTransition),
      heightCs: cs(pageTransition, 'height'),
      inlineHeight: pageTransition?.style?.height ?? null,
    },
    lesson: rect(lesson),
    stage: rect(stage),
    board: rect(board),
    panel: rect(panel),
    tutorialPage: rect(tutorialPage),
    render: {
      cellCount: document.querySelectorAll('.tutorial-lesson .kletka').length,
      sampleCell: rect(sampleCell),
      cellDisplay: cs(sampleCell, 'display'),
      cellWidth: cs(sampleCell, 'width'),
      cellHeight: cs(sampleCell, 'height'),
      rowDisplay: cs(sampleRow, 'display'),
      boardUnit: cs(board, '--board-unit')?.trim() ?? null,
      boardHeightUnits: cs(board, '--board-height-units')?.trim() ?? null,
      cellHighlightRing: boardCs?.getPropertyValue('--cell-highlight-ring')?.trim() ?? null,
      cellBorderWidth: boardCs?.getPropertyValue('--cell-border-width')?.trim() ?? null,
      highlightEssentialShadow: cellCs?.boxShadow ?? null,
      boardCssLoaded: cs(sampleRow, 'display') === 'flex',
      isLite: board?.classList.contains('board--lite') ?? false,
      isCanvas: Boolean(document.querySelector('.tutorial-lesson .board-canvas')),
      layoutSnapshot,
    },
    chromeOffset: cs(document.documentElement, '--app-top-chrome-offset'),
    lobbyNavClear: cs(document.documentElement, '--lobby-nav-clear-top'),
    broken:
      (lesson && (lesson.getBoundingClientRect().height < 120))
      || (board && board.getBoundingClientRect().height < 80)
      || (pageTransition && pageTransition.getBoundingClientRect().height < 80)
      || (sampleCell && sampleCell.getBoundingClientRect().height < 30 && sampleCell.getBoundingClientRect().width > 100),
    stageOverflow:
      stage && board
        ? board.getBoundingClientRect().bottom > stage.getBoundingClientRect().bottom + 1
          || board.getBoundingClientRect().top < stage.getBoundingClientRect().top - 1
        : null,
    ...extra,
  };

  sendDevProbe({
    sessionId: 'dev',
    hypothesisId: 'tutorial-layout',
    location: 'tutorialLayoutProbe.js',
    message: 'tutorial layout probe',
    data,
  });

  return data;
}
