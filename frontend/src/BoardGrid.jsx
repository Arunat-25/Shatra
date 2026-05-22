import { BOARD_SECTIONS } from './constants';
import Cell from './components/Cell';

export default function BoardGrid({ board, onCellClick, moveFrom, highlightedEssential = [], highlightedCaptured = [], lastMove = null, historyFrom = null, historyTo = null }) {
  return (
    <>
      {BOARD_SECTIONS.map((section) => (
        <div key={`${section.class}-${section.rows[0]?.[0]?.id ?? 0}`} className={section.class}>
          {section.rows.map((row, rowIdx) => (
            <div key={rowIdx} className="row">
              {row.map((cell) => (
                  <Cell
                    key={cell.id}
                    id={cell.id}
                    className={cell.color}
                    board={board}
                    moveFrom={moveFrom}
                    highlightedEssential={highlightedEssential}
                    highlightedCaptured={highlightedCaptured}
                    lastMove={lastMove}
                    historyFrom={historyFrom}
                    historyTo={historyTo}
                    onCellClick={onCellClick}
                  />
              ))}
            </div>
          ))}
        </div>
      ))}
    </>
  );
}