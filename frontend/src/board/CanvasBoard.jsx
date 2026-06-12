import { useCallback, useEffect, useRef } from 'react';
import { computeBoardLayout, hitTestCell } from './layoutMetrics';
import { drawBoardFrame, drawBoardState } from './drawBoard';
import useBoardInteraction from '../hooks/useBoardInteraction';

export default function CanvasBoard({
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
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const layoutRef = useRef(null);
  const rafRef = useRef(null);
  const dragGhostDrawRef = useRef(null);

  const resolveCellAt = useCallback((clientX, clientY) => {
    const canvas = canvasRef.current;
    const layout = layoutRef.current;
    if (!canvas || !layout) return null;
    const rect = canvas.getBoundingClientRect();
    // Layout is in CSS pixels (ctx.setTransform(dpr) scales drawing, not coords).
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return hitTestCell(layout.cells, x, y);
  }, []);

  const { beginDrag, handleCellClick, registerDragGhostListener } = useBoardInteraction({
    board,
    onCellClick,
    moveFrom,
    interactive,
    enablePieceDrag,
    resolveCellAt,
  });

  const paint = useCallback(() => {
    const canvas = canvasRef.current;
    const layout = layoutRef.current;
    if (!canvas || !layout) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawBoardFrame(ctx, layout);

    let dragGhost = dragGhostDrawRef.current;
    if (dragGhost?.piece) {
      const rect = canvas.getBoundingClientRect();
      dragGhost = {
        ...dragGhost,
        x: dragGhost.x - rect.left,
        y: dragGhost.y - rect.top,
      };
    }

    drawBoardState(ctx, layout, {
      board,
      moveFrom,
      highlightedEssential,
      highlightedCaptured,
      capturedGhostPieces,
      lastMove,
      historyFrom,
      historyTo,
      dragGhost,
    });
  }, [
    board,
    moveFrom,
    highlightedEssential,
    highlightedCaptured,
    capturedGhostPieces,
    lastMove,
    historyFrom,
    historyTo,
  ]);

  const schedulePaint = useCallback(() => {
    if (rafRef.current != null) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      paint();
    });
  }, [paint]);

  const resizeCanvas = useCallback(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const dpr = window.devicePixelRatio || 1;
    const w = Math.max(1, Math.floor(container.clientWidth));
    let h = Math.floor(container.clientHeight);

    if (h < 50) {
      const innerW = Math.max(0, w - 6);
      const unit = (innerW - 10) / 7;
      h = Math.max(1, Math.ceil(unit * 13.6 + 10 + 6 + 5));
      container.style.height = `${h}px`;
    }

    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;

    const ctx = canvas.getContext('2d');
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    layoutRef.current = computeBoardLayout(myColor, w, h);
    schedulePaint();
  }, [myColor, schedulePaint]);

  useEffect(() => {
    resizeCanvas();
    const ro = typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver(resizeCanvas)
      : null;
    if (containerRef.current) ro?.observe(containerRef.current);
    window.addEventListener('resize', resizeCanvas);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', resizeCanvas);
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [resizeCanvas]);

  useEffect(() => {
    schedulePaint();
  }, [schedulePaint]);

  useEffect(
    () => registerDragGhostListener((ghost) => {
      dragGhostDrawRef.current = ghost;
      schedulePaint();
    }),
    [registerDragGhostListener, schedulePaint],
  );

  const onPointerDown = useCallback((event) => {
    if (!interactive) return;
    if (event.button != null && event.button !== 0) return;
    const cellId = resolveCellAt(event.clientX, event.clientY);
    if (cellId == null) return;
    event.preventDefault();
    const piece = board[cellId];
    if (piece && enablePieceDrag) {
      const layout = layoutRef.current;
      const cell = layout?.cells[cellId];
      const size = cell ? Math.round(cell.w) : undefined;
      event.currentTarget.setPointerCapture?.(event.pointerId);
      beginDrag(cellId, event, size);
      schedulePaint();
      return;
    }
    handleCellClick(cellId);
  }, [
    interactive,
    resolveCellAt,
    board,
    enablePieceDrag,
    beginDrag,
    handleCellClick,
    schedulePaint,
  ]);

  return (
    <div ref={containerRef} className="board-content board-content--canvas">
      <canvas
        ref={canvasRef}
        className="board-canvas"
        aria-hidden
        onPointerDown={onPointerDown}
      />
    </div>
  );
}
