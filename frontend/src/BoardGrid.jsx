import { useCallback, useState } from 'react';
import { getBoardSections } from './constants';
import Cell from './components/Cell';
import ShatraPiece from './ShatraPiece';
import { getPieceColor, getPieceType } from './utils';
import useBoardInteraction from './hooks/useBoardInteraction';

function cellIdFromPoint(x, y) {
  const el = document.elementFromPoint(x, y);
  const cell = el?.closest?.('.kletka');
  if (!cell?.id?.startsWith('position')) return null;
  const id = Number.parseInt(cell.id.slice('position'.length), 10);
  return Number.isFinite(id) ? id : null;
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
    tutorialDimmedCells = null,
    pieceVariant = 'full',
  } = props;
  const sections = getBoardSections(myColor);
  const tutorialDimmedSet = tutorialDimmedCells ? new Set(tutorialDimmedCells) : null;

  const resolveCellAt = useCallback((x, y) => cellIdFromPoint(x, y), []);

  const { beginDrag, handleCellClick, registerDragGhostListener } = useBoardInteraction({
    board,
    onCellClick,
    moveFrom,
    interactive,
    enablePieceDrag,
    resolveCellAt,
  });

  const [dragGhost, setDragGhost] = useState(null);
  registerDragGhostListener(useCallback((ghost) => setDragGhost(ghost), []));

  const onPointerDown = useCallback((cellId, event) => {
    const cellEl = event.currentTarget;
    const cellSize = cellEl ? Math.round(cellEl.getBoundingClientRect().width) : undefined;
    beginDrag(cellId, event, cellSize);
  }, [beginDrag]);

  const shouldIgnoreClick = useCallback(() => false, []);
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
              variant={pieceVariant}
            />
          </div>
        </div>
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
