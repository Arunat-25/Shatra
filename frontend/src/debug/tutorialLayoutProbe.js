const ENDPOINT = 'http://127.0.0.1:7570/ingest/7c8a0073-ab4a-4548-b425-fe00951377e1';
const SESSION = '97ed31';

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

export function probeTutorialLayout(tag, extra = {}) {
  const shell = document.querySelector('.app-shell');
  const appMain = document.querySelector('.app-main');
  const pageTransition = document.querySelector('.page-transition');
  const lesson = document.querySelector('.tutorial-lesson');
  const board = document.querySelector('.tutorial-lesson .board');
  const panel = document.querySelector('.tutorial-lesson__panel');
  const tutorialPage = document.querySelector('.tutorial-page');
  const sampleCell = document.querySelector('.tutorial-lesson .field-of-king .kletka');
  const sampleRow = document.querySelector('.tutorial-lesson .field-of-king .row');

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
      boardCssLoaded: cs(sampleRow, 'display') === 'flex',
    },
    chromeOffset: cs(document.documentElement, '--app-top-chrome-offset'),
    lobbyNavClear: cs(document.documentElement, '--lobby-nav-clear-top'),
    broken:
      (lesson && (lesson.getBoundingClientRect().height < 120))
      || (board && board.getBoundingClientRect().height < 80)
      || (pageTransition && pageTransition.getBoundingClientRect().height < 80)
      || (sampleCell && sampleCell.getBoundingClientRect().height < 30 && sampleCell.getBoundingClientRect().width > 100),
    ...extra,
  };

  // #region agent log
  fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': SESSION },
    body: JSON.stringify({
      sessionId: SESSION,
      location: 'tutorialLayoutProbe.js',
      message: 'tutorial layout probe',
      hypothesisId: 'H1-H5',
      data,
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion

  return data;
}
