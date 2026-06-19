import { useCallback, useEffect, useMemo, useState } from 'react';
import { getBoardSections } from './constants';
import Cell from './components/Cell';
import ShatraPiece from './ShatraPiece';
import { getPieceColor, getPieceType } from './utils';
import useBoardInteraction from './hooks/useBoardInteraction';
import usePieceSlideOverlay from './hooks/usePieceSlideOverlay';

function cellIdFromPoint(x, y) {
  const elements = typeof document.elementsFromPoint === 'function'
    ? document.elementsFromPoint(x, y)
    : [document.elementFromPoint(x, y)].filter(Boolean);
  for (const el of elements) {
    if (el?.closest?.('.drag-ghost, .piece-slide-ghost')) continue;
    const cell = el?.closest?.('.kletka');
    if (!cell?.id?.startsWith('position')) continue;
    const id = Number.parseInt(cell.id.slice('position'.length), 10);
    if (Number.isFinite(id)) return id;
  }

  const cells = document.querySelectorAll('.board-content .kletka');
  for (const cell of cells) {
    const r = cell.getBoundingClientRect();
    if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom) {
      const id = Number.parseInt(cell.id.slice('position'.length), 10);
      if (Number.isFinite(id)) return id;
    }
  }
  return null;
}

function domCellCenter(cellId) {
  const el = document.getElementById(`position${cellId}`);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {
    x: r.left + r.width / 2,
    y: r.top + r.height / 2,
    size: r.width,
  };
}

function domCellBounds(cellId) {
  const el = document.getElementById(`position${cellId}`);
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return {
    left: r.left,
    top: r.top,
    right: r.right,
    bottom: r.bottom,
  };
}

function PieceOverlay({ overlay, pieceVariant, className }) {
  if (!overlay?.piece) return null;
  return (
    <div
      className={className}
      style={{ transform: `translate(${overlay.x}px, ${overlay.y}px)` }}
    >
      <div
        className="drag-ghost-inner piece-slide-inner"
        style={
          overlay.size
            ? { width: overlay.size, height: overlay.size }
            : undefined
        }
      >
        <ShatraPiece
          type={getPieceType(overlay.piece)}
          color={getPieceColor(overlay.piece)}
          isSelected={false}
          isTarget={false}
          positionNum={overlay.fromCell ?? overlay.toCell ?? 0}
          variant={pieceVariant}
        />
      </div>
    </div>
  );
}

export default function BoardGrid(props) {
  const {
    board,
    onCellClick,
    moveFrom,
    highlightedEssential = [],
    highlightedCaptured = [],
    capturedGhostPieces = {},
    lastMove = null,
    historyFrom = null,
    historyTo = null,
    myColor,
    interactive = true,
    enablePieceDrag = true,
    enableMoveAnimation = true,
    getDragLegalDests = null,
    tutorialDimmedCells = null,
    pieceVariant = 'full',
  } = props;
  const sections = getBoardSections(myColor);
  const tutorialDimmedSet = tutorialDimmedCells ? new Set(tutorialDimmedCells) : null;

  const resolveCellAt = useCallback((x, y) => cellIdFromPoint(x, y), []);
  const getCellCenter = useCallback((cellId) => domCellCenter(cellId), []);
  const getCellBounds = useCallback((cellId) => domCellBounds(cellId), []);
  const legalDests = useMemo(
    () => new Set(highlightedEssential),
    [highlightedEssential],
  );

  const { slideOverlay, markSlideHandled } = usePieceSlideOverlay({
    lastMove,
    board,
    getCellCenter,
    enabled: interactive && enableMoveAnimation,
  });

  const onDragDropComplete = useCallback((from, to) => {
    markSlideHandled(from, to);
  }, [markSlideHandled]);

  const { beginDrag, handleCellClick, registerDragGhostListener } = useBoardInteraction({
    board,
    onCellClick,
    moveFrom,
    interactive,
    enablePieceDrag,
    resolveCellAt,
    legalDests,
    getLegalDests: getDragLegalDests,
    getCellCenter,
    getCellBounds,
    onDragDropComplete,
  });

  const [dragGhost, setDragGhost] = useState(null);

  useEffect(() => {
    return registerDragGhostListener(setDragGhost);
  }, [registerDragGhostListener]);

  const onPointerDown = useCallback((cellId, event) => {
    const cellEl = event.currentTarget;
    const cellSize = cellEl ? Math.round(cellEl.getBoundingClientRect().width) : undefined;
    beginDrag(cellId, event, cellSize);
  }, [beginDrag]);

  const shouldIgnoreClick = useCallback(() => false, []);
  const noop = useCallback(() => {}, []);

  const hidePieceCells = useMemo(() => {
    const hidden = new Set();
    if (slideOverlay?.toCell != null) hidden.add(slideOverlay.toCell);
    return hidden;
  }, [slideOverlay]);

  const isDragging = Boolean(dragGhost);

  return (
    <div className={isDragging ? 'board-content board-content--dragging' : 'board-content'}>
      {interactive && dragGhost && (
        <PieceOverlay
          overlay={dragGhost}
          pieceVariant={pieceVariant}
          className="drag-ghost"
        />
      )}
      {interactive && slideOverlay && !dragGhost && (
        <PieceOverlay
          overlay={slideOverlay}
          pieceVariant={pieceVariant}
          className="piece-slide-ghost"
        />
      )}
      {sections.map((section) => (
        <div
          key={`${section.class}-${section.rows?.[0]?.[0]?.id ?? 0}`}
          className={section.class}
        >
          {section.rows.map((row, rowIdx) => (
            <div key={rowIdx} className="row">
              {row.map((cell) => (
                <Cell
                  key={cell.id}
                  id={cell.id}
                  className={cell.color}
                  isDragOrigin={interactive && dragGhost?.fromId === cell.id}
                  hidePiece={hidePieceCells.has(cell.id)}
                  isTutorialDimmed={tutorialDimmedSet?.has(cell.id)}
                  onCellPointerDown={interactive && enablePieceDrag ? onPointerDown : undefined}
                  shouldIgnoreClick={interactive && enablePieceDrag ? shouldIgnoreClick : undefined}
                  onCellClick={interactive ? handleCellClick : noop}
                  pieceVariant={pieceVariant}
                  {...{
                    board,
                    moveFrom: interactive ? moveFrom : null,
                    highlightedEssential: interactive ? highlightedEssential : [],
                    highlightedCaptured: interactive ? highlightedCaptured : [],
                    capturedGhostPiece: interactive ? capturedGhostPieces[cell.id] : null,
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
