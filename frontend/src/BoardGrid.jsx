import { BOARD_SECTIONS } from './constants';
import Cell from './components/Cell';

export default function BoardGrid(props) {
  const { board, onCellClick, moveFrom, highlightedEssential = [], highlightedCaptured = [], lastMove = null, historyFrom = null, historyTo = null } = props;
  return (
    <>
      {BOARD_SECTIONS.map((section) => (
        <div key={`${section.class}-${section.rows?.[0]?.[0]?.id ?? 0}`} className={section.class}>
          {section.rows.map((row, rowIdx) => (
            <div key={rowIdx} className="row">
              {row.map((cell) => (
                  <Cell
                    key={cell.id}
                    id={cell.id}
                    className={cell.color}
                    {...{ board, moveFrom, highlightedEssential, highlightedCaptured, lastMove, historyFrom, historyTo, onCellClick }}
                  />
              ))}
            </div>
          ))}
        </div>
      ))}
    </>
  );
}
