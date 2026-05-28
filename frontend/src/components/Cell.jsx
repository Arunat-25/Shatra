import { memo } from 'react';
import ShatraPiece from '../ShatraPiece';
import { getPieceType, getPieceColor } from '../utils';

function cellClass(id, className, board, moveFrom, hE, hC, lastMove, hF, hT) {
  return [
    'kletka', className,
    board[id] ? 'has-piece' : '',
    // During drag, we dim the origin cell's piece but keep the number visible.
    // (the actual dragged piece is rendered as an overlay ghost)
    moveFrom === id ? 'highlight-black' : '',
    hE.includes(id) ? 'highlight-essential' : '',
    hC.includes(id) ? 'highlight-captured' : '',
    lastMove && lastMove.from === id ? 'last-move-from' : '',
    lastMove && lastMove.to === id ? 'last-move-to' : '',
    hF === id ? 'cell-history-from' : '',
    hT === id ? 'cell-history-to' : '',
  ].filter(Boolean).join(' ');
}

const Cell = memo(function Cell(props) {
  const { id, className, board, moveFrom, highlightedEssential = [], highlightedCaptured = [],
          lastMove = null, historyFrom = null, historyTo = null, onCellClick,
          onCellPointerDown, onCellPointerUp, shouldIgnoreClick, isDragOrigin } = props;
  const piece = board[id];

  return (
    <div
      id={`position${id}`}
      className={[
        cellClass(id, className, board, moveFrom, highlightedEssential,
          highlightedCaptured, lastMove, historyFrom, historyTo),
        isDragOrigin ? 'drag-origin' : '',
      ].filter(Boolean).join(' ')}
      onClick={() => {
        if (shouldIgnoreClick?.()) return;
        onCellClick(id);
      }}
      onPointerDown={(e) => {
        if (!piece) return;
        // Only left click / primary touch
        if (e.button != null && e.button !== 0) return;
        onCellPointerDown?.(id);
      }}
      onPointerUp={(e) => {
        if (e.button != null && e.button !== 0) return;
        onCellPointerUp?.(id);
      }}
    >
      <span className="cell-number">{id}</span>
      {piece && (
        <div className="image-in-kletka" draggable={false}>
          <ShatraPiece
            type={getPieceType(piece)}
            color={getPieceColor(piece)}
            isSelected={moveFrom === id}
            isTarget={highlightedCaptured.includes(id)}
            positionNum={id}
          />
        </div>
      )}
    </div>
  );
});

export default Cell;