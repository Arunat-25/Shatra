import { useCallback, useEffect, useRef, useState } from 'react';
import { getBoardSections } from './constants';
import Cell from './components/Cell';
import ShatraPiece from './ShatraPiece';
import { getPieceColor, getPieceType } from './utils';

export default function BoardGrid(props) {
  const { board, onCellClick, moveFrom, highlightedEssential = [], highlightedCaptured = [], lastMove = null, historyFrom = null, historyTo = null, myColor } = props;
  const sections = getBoardSections(myColor);

  const dragFromRef = useRef(null);
  const dragStartedAtRef = useRef(0);
  const ignoreClickUntilRef = useRef(0);
  const [dragGhost, setDragGhost] = useState(null); // { fromId, piece, x, y }

  const beginDrag = useCallback((cellId) => {
    const piece = board[cellId];
    if (!piece) return;
    dragFromRef.current = cellId;
    dragStartedAtRef.current = Date.now();
    // Prevent the subsequent synthetic click from immediately deselecting the piece
    // (pointerdown selects, then click fires and toggles selection off).
    ignoreClickUntilRef.current = Date.now() + 250;
    onCellClick(cellId); // select piece (or no-op if invalid)
    setDragGhost((prev) => (prev && prev.fromId === cellId ? prev : { fromId: cellId, piece, x: 0, y: 0 }));
  }, [onCellClick, board]);

  const endDrag = useCallback((cellId) => {
    const from = dragFromRef.current;
    dragFromRef.current = null;
    setDragGhost(null);
    if (from == null) return;

    // Only treat as drag if it lasted at least a few ms (avoid messing with normal click)
    const elapsed = Date.now() - (dragStartedAtRef.current || 0);
    if (elapsed < 50) return;

    if (from !== cellId) {
      ignoreClickUntilRef.current = Date.now() + 250;
      onCellClick(cellId); // attempt move
    }
  }, [onCellClick]);

  const shouldIgnoreClick = useCallback(() => Date.now() < ignoreClickUntilRef.current, []);

  useEffect(() => {
    if (!dragGhost) return undefined;
    const onMove = (e) => {
      setDragGhost((g) => (g ? { ...g, x: e.clientX, y: e.clientY } : g));
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => window.removeEventListener('pointermove', onMove);
  }, [dragGhost]);

  return (
    <div className="board-content">
      {dragGhost && (
        <div
          className="drag-ghost"
          style={{ transform: `translate(${dragGhost.x}px, ${dragGhost.y}px)` }}
        >
          <div className="drag-ghost-inner">
            <ShatraPiece
              type={getPieceType(dragGhost.piece)}
              color={getPieceColor(dragGhost.piece)}
              isSelected={false}
              isTarget={false}
              positionNum={dragGhost.fromId}
            />
          </div>
        </div>
      )}
      {sections.map((section) => (
        <div key={`${section.class}-${section.rows?.[0]?.[0]?.id ?? 0}`} className={section.class}>
          {section.rows.map((row, rowIdx) => (
            <div key={rowIdx} className="row">
              {row.map((cell) => (
                  <Cell
                    key={cell.id}
                    id={cell.id}
                    className={cell.color}
                    isDragOrigin={dragGhost?.fromId === cell.id}
                    onCellPointerDown={beginDrag}
                    onCellPointerUp={endDrag}
                    shouldIgnoreClick={shouldIgnoreClick}
                    {...{ board, moveFrom, highlightedEssential, highlightedCaptured, lastMove, historyFrom, historyTo, onCellClick }}
                  />
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
