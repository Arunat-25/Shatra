import { memo } from 'react';
import ShatraPiece from '../ShatraPiece';
import { getPieceType, getPieceColor } from '../utils';

function cellClass(id, className, moveFrom, hE, hC, lastMove, hF, hT, isCapturedGhost) {
  return [
    'kletka', className,
    moveFrom === id ? 'highlight-black' : '',
    hE.includes(id) ? 'highlight-essential' : '',
    hC.includes(id) && !isCapturedGhost ? 'highlight-captured' : '',
    lastMove && lastMove.from === id ? 'last-move-from' : '',
    lastMove && lastMove.to === id ? 'last-move-to' : '',
    hF === id ? 'cell-history-from' : '',
    hT === id ? 'cell-history-to' : '',
  ].filter(Boolean).join(' ');
}

const Cell = memo(function Cell(props) {
  const { id, className, board, moveFrom, highlightedEssential = [], highlightedCaptured = [],
          lastMove = null, historyFrom = null, historyTo = null, onCellClick,
          onCellPointerDown, shouldIgnoreClick, isDragOrigin, isTutorialDimmed,
          capturedGhostPiece = null, pieceVariant = 'full' } = props;
  const piece = board[id];
  const renderedPiece = piece || capturedGhostPiece;
  const isCapturedGhost = !piece && !!capturedGhostPiece;

  return (
    <div
      id={`position${id}`}
      className={[
        cellClass(id, className, moveFrom, highlightedEssential,
          highlightedCaptured, lastMove, historyFrom, historyTo, isCapturedGhost),
        isCapturedGhost ? 'captured-ghost-cell' : '',
        isDragOrigin ? 'drag-origin' : '',
        isTutorialDimmed ? 'tutorial-cell-dimmed' : '',
      ].filter(Boolean).join(' ')}
      onClick={() => {
        if (shouldIgnoreClick?.()) return;
        onCellClick(id);
      }}
      onPointerDown={(e) => {
        if (!piece) return;
        if (e.button != null && e.button !== 0) return;
        e.preventDefault();
        onCellPointerDown?.(id, e);
      }}
    >
      <span className="cell-number">{id}</span>
      {renderedPiece && (
        <div
          className={[
            'image-in-kletka',
            isCapturedGhost ? 'captured-ghost-piece' : '',
          ].filter(Boolean).join(' ')}
          draggable={false}
        >
          <ShatraPiece
            type={getPieceType(renderedPiece)}
            color={getPieceColor(renderedPiece)}
            isSelected={!isCapturedGhost && moveFrom === id}
            isTarget={!isCapturedGhost && highlightedCaptured.includes(id)}
            positionNum={id}
            variant={pieceVariant}
          />
        </div>
      )}
    </div>
  );
});

export default Cell;
