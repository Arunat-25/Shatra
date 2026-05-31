import { useCallback, useEffect, useRef, useState } from 'react';
import { getBoardSections } from './constants';
import Cell from './components/Cell';
import ShatraPiece from './ShatraPiece';
import { getPieceColor, getPieceType } from './utils';

const SECTION_ZONE = {
  'field-of-reserve': 'fortress',
  'field-of-king': 'gate',
  'main-field': 'main',
};

function cellIdFromPoint(x, y) {
  const el = document.elementFromPoint(x, y);
  const cell = el?.closest?.('.kletka');
  if (!cell?.id?.startsWith('position')) return null;
  const id = Number.parseInt(cell.id.slice('position'.length), 10);
  return Number.isFinite(id) ? id : null;
}

function sectionClassName(sectionClass, highlightZones) {
  const zone = SECTION_ZONE[sectionClass];
  if (!zone || !highlightZones?.includes(zone)) {
    return sectionClass;
  }
  return `${sectionClass} tutorial-zone tutorial-zone--${zone}`;
}

export default function BoardGrid(props) {
  const {
    board,
    onCellClick,
    moveFrom,
    highlightedEssential = [],
    highlightedCaptured = [],
    lastMove = null,
    historyFrom = null,
    historyTo = null,
    myColor,
    interactive = true,
    highlightZones = null,
    spotlightCells = null,
  } = props;
  const sections = getBoardSections(myColor);
  const spotlightSet = spotlightCells ? new Set(spotlightCells) : null;

  const dragFromRef = useRef(null);
  const dragStartedAtRef = useRef(0);
  const activePointerIdRef = useRef(null);
  const ignoreClickUntilRef = useRef(0);
  const dragListenersRef = useRef(null);
  const [dragGhost, setDragGhost] = useState(null);

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
    if (!interactive) return;
    const piece = board[cellId];
    if (!piece || !event) return;
    if (event.button != null && event.button !== 0) return;

    event.preventDefault();

    clearDragListeners();

    dragFromRef.current = cellId;
    dragStartedAtRef.current = Date.now();
    activePointerIdRef.current = event.pointerId;
    ignoreClickUntilRef.current = Date.now() + 250;
    if (moveFrom !== cellId) {
      onCellClick(cellId);
    }

    const cellEl = event.currentTarget;
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
      finishDrag(e);
    };

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', onFinish);
    window.addEventListener('pointercancel', onFinish);
    dragListenersRef.current = { onMove, onFinish };
  }, [board, interactive, moveFrom, onCellClick, clearDragListeners, finishDrag]);

  const shouldIgnoreClick = useCallback(() => Date.now() < ignoreClickUntilRef.current, []);

  useEffect(() => () => clearDragListeners(), [clearDragListeners]);

  const noop = useCallback(() => {}, []);

  return (
    <div className={dragGhost ? 'board-content board-content--dragging' : 'board-content'}>
      {interactive && dragGhost && (
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
        <div
          key={`${section.class}-${section.rows?.[0]?.[0]?.id ?? 0}`}
          className={sectionClassName(section.class, highlightZones)}
        >
          {section.rows.map((row, rowIdx) => (
            <div key={rowIdx} className="row">
              {row.map((cell) => (
                <Cell
                  key={cell.id}
                  id={cell.id}
                  className={cell.color}
                  isDragOrigin={interactive && dragGhost?.fromId === cell.id}
                  isSpotlight={spotlightSet?.has(cell.id)}
                  onCellPointerDown={interactive ? beginDrag : undefined}
                  shouldIgnoreClick={interactive ? shouldIgnoreClick : undefined}
                  onCellClick={interactive ? onCellClick : noop}
                  {...{
                    board,
                    moveFrom: interactive ? moveFrom : null,
                    highlightedEssential: interactive ? highlightedEssential : [],
                    highlightedCaptured: interactive ? highlightedCaptured : [],
                    lastMove: interactive ? lastMove : null,
                    historyFrom: interactive ? historyFrom : null,
                    historyTo: interactive ? historyTo : null,
                  }}
                />
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
