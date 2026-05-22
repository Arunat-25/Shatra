import ShatraPiece from '../ShatraPiece';
import { getPieceType, getPieceColor } from '../utils';

function getCellClasses(id, className, board, moveFrom, highlightedEssential, highlightedCaptured, lastMove, historyFrom, historyTo) {
  return [
    'kletka',
    className,
    board[id] ? 'has-piece' : '',
    moveFrom === id ? 'highlight-black' : '',
    highlightedEssential.includes(id) ? 'highlight-essential' : '',
    highlightedCaptured.includes(id) ? 'highlight-captured' : '',
    lastMove && lastMove.from === id ? 'last-move-from' : '',
    lastMove && lastMove.to === id ? 'last-move-to' : '',
    historyFrom === id ? 'cell-history-from' : '',
    historyTo === id ? 'cell-history-to' : '',
  ].filter(Boolean).join(' ');
}

export default function Cell({ id, className, board, moveFrom, highlightedEssential, highlightedCaptured, lastMove, historyFrom, historyTo, onCellClick }) {
  return (
    <div
      key={id}
      id={`position${id}`}
      className={getCellClasses(id, className, board, moveFrom, highlightedEssential, highlightedCaptured, lastMove, historyFrom, historyTo)}
      onClick={() => onCellClick(id)}
    >
      {board[id] && (
        <div className="image-in-kletka">
          <ShatraPiece
            type={getPieceType(board[id])}
            color={getPieceColor(board[id])}
            isSelected={moveFrom === id}
            isTarget={highlightedCaptured.includes(id)}
            positionNum={id}
          />
        </div>
      )}
    </div>
  );
}