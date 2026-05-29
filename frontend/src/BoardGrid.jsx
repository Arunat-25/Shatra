import { useCallback, useEffect, useRef, useState } from 'react';
import { getBoardSections } from './constants';
import Cell from './components/Cell';
import ShatraPiece from './ShatraPiece';
import { getPieceColor, getPieceType } from './utils';

function cellIdFromPoint(x, y) {
  const el = document.elementFromPoint(x, y);
  const cell = el?.closest?.('.kletka');
  if (!cell?.id?.startsWith('position')) return null;
  const id = Number.parseInt(cell.id.slice('position'.length), 10);
  return Number.isFinite(id) ? id : null;
}

export default function BoardGrid(props) {
  const { board, onCellClick, moveFrom, highlightedEssential = [], highlightedCaptured = [], lastMove = null, historyFrom = null, historyTo = null, myColor } = props;
  const sections = getBoardSections(myColor);

  const dragFromRef = useRef(null);
  const dragStartedAtRef = useRef(0);
  const activePointerIdRef = useRef(null);
  const ignoreClickUntilRef = useRef(0);
  const dragListenersRef = useRef(null);
  const [dragGhost, setDragGhost] = useState(null); // { fromId, piece, x, y, size }

  const clearDragListeners = useCallback(() => {
    const listeners = dragListenersRef.current;
    if (!listeners) return;
    window.removeEventListener('pointermove', listeners.onMove);
    window.removeEventListener('pointerup', listeners.onFinish);
    window.removeEventListener('pointercancel', listeners.onFinish);
    dragListenersRef.current = null;
  }, []);

  const finishDrag = useCallback((event) => {
    if (activePointerIdRef.current != null && event.pointerId !== activePointerIdRef.current) {
      return;
    }

    clearDragListeners();

    const from = dragFromRef.current;
    dragFromRef.current = null;
    activePointerIdRef.current = null;
    setDragGhost(null);

    if (from == null) return;

    const elapsed = Date.now() - (dragStartedAtRef.current || 0);
    if (elapsed < 50) return;

    const targetCellId = cellIdFromPoint(event.clientX, event.clientY);
    if (targetCellId != null && from !== targetCellId) {
      ignoreClickUntilRef.current = Date.now() + 250;
      onCellClick(targetCellId);
    }
  }, [clearDragListeners, onCellClick]);

  const beginDrag = useCallback((cellId, event) => {
    const piece = board[cellId];
    if (!piece || !event) return;
    if (event.button != null && event.button !== 0) return;

    clearDragListeners();

    dragFromRef.current = cellId;
    dragStartedAtRef.current = Date.now();
    activePointerIdRef.current = event.pointerId;
    ignoreClickUntilRef.current = Date.now() + 250;
    onCellClick(cellId);

    const cellEl = event.currentTarget;
    try {
      cellEl.setPointerCapture(event.pointerId);
    } catch {
      // Some browsers reject capture on unsupported targets.
    }

    const cellSize = cellEl ? Math.round(cellEl.getBoundingClientRect().width) : undefined;
    setDragGhost({
      fromId: cellId,
      piece,
      x: event.clientX,
      y: event.clientY,
      size: cellSize,
    });

    const onMove = (e) => {
      if (e.pointerId !== event.pointerId) return;
      setDragGhost((ghost) => (ghost ? { ...ghost, x: e.clientX, y: e.clientY } : ghost));
    };

    const onFinish = (e) => {
      if (e.pointerId !== event.pointerId) return;
      try {
        cellEl.releasePointerCapture(event.pointerId);
      } catch {
        // Ignore if capture was already released.
      }
      finishDrag(e);
    };

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', onFinish);
    window.addEventListener('pointercancel', onFinish);
    dragListenersRef.current = { onMove, onFinish };
  }, [board, onCellClick, clearDragListeners, finishDrag]);

  const shouldIgnoreClick = useCallback(() => Date.now() < ignoreClickUntilRef.current, []);

  useEffect(() => () => clearDragListeners(), [clearDragListeners]);

  return (
    <div className="board-content">
      {dragGhost && (
        <div
          className="drag-ghost"
          style={{ transform: `translate(${dragGhost.x}px, ${dragGhost.y}px)` }}
        >
          <div
            className="drag-ghost-inner"
            style={
              dragGhost.size
                ? { width: dragGhost.size, height: dragGhost.size }
                : undefined
            }
          >
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
