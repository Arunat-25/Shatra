import { useTranslation } from 'react-i18next';
import { useLiteUi } from '../../context/LiteUiContext';
import BoardGrid from '../../BoardGrid';

const noop = () => {};

export default function TutorialLessonLayout({
  board,
  text,
  onNext,
  onBack,
  onTryAgain,
  canGoBack = false,
  showTryAgain = false,
  tutorialDimmedCells = null,
  highlightedEssential = [],
  highlightedCaptured = [],
  capturedGhostPieces = {},
  interactive = false,
  onCellClick,
  moveFrom = null,
  canProceed = true,
  instruction = null,
  showPassTurn = false,
  onPassTurn,
}) {
  const { t } = useTranslation();
  const { enabled: liteUi } = useLiteUi();

  const boardClass = ['board', interactive ? '' : 'disabled'].filter(Boolean).join(' ');

  return (
    <div className="tutorial-lesson">
      <div className="tutorial-lesson__stage">
        <div className="room-board-wrap">
          <div className="room-board">
            <div className={boardClass}>
              <BoardGrid
                board={board}
                onCellClick={interactive && onCellClick ? onCellClick : noop}
                myColor="белый"
                interactive={interactive}
                enablePieceDrag={false}
                pieceVariant={liteUi ? 'lite' : 'full'}
                tutorialDimmedCells={tutorialDimmedCells}
                highlightedEssential={highlightedEssential}
                highlightedCaptured={highlightedCaptured}
                capturedGhostPieces={capturedGhostPieces}
                moveFrom={moveFrom}
              />
            </div>
          </div>
        </div>
      </div>
      <aside className="tutorial-lesson__panel">
        <div className="tutorial-lesson__panel-body">
          <p className="tutorial-lesson__text">{text}</p>
          {instruction && (
            <p className="tutorial-lesson__instruction">{instruction}</p>
          )}
          {showTryAgain && onTryAgain && (
            <button
              type="button"
              className="tutorial-lesson__again"
              onClick={onTryAgain}
            >
              {t('tutorial.tryAgain')}
            </button>
          )}
          {showPassTurn && onPassTurn && (
            <button
              type="button"
              className="tutorial-lesson__pass"
              onClick={onPassTurn}
            >
              {t('tutorial.passTurn')}
            </button>
          )}
        </div>
        <div className="tutorial-lesson__panel-nav">
          <div className="tutorial-lesson__nav">
            <button
              type="button"
              className="tutorial-lesson__prev"
              onClick={onBack}
              disabled={!canGoBack}
            >
              {t('tutorial.prev')}
            </button>
            <button
              type="button"
              className="tutorial-lesson__next"
              onClick={onNext}
              disabled={!canProceed}
            >
              {t('tutorial.next')}
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}
