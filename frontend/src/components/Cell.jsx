import { memo } from 'react';
import ShatraPiece from '../ShatraPiece';
import { getPieceType, getPieceColor } from '../utils';

function cellClass(id, className, board, moveFrom, hE, hC, lastMove, hF, hT) {
  return [
    'kletka', className,
    board[id] ? 'has-piece' : '',
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
          lastMove = null, historyFrom = null, historyTo = null, onCellClick } = props;
  const piece = board[id];

  return (
    <div
      id={`position${id}`}
      className={cellClass(id, className, board, moveFrom, highlightedEssential,
                           highlightedCaptured, lastMove, historyFrom, historyTo)}
      onClick={() => onCellClick(id)}
    >
      <span className="cell-number">{id}</span>
      {piece && (
        <div className="image-in-kletka">
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