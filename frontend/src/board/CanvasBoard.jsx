import { useCallback, useEffect, useRef } from 'react';
import { computeBoardLayout, hitTestCell } from './layoutMetrics';
import { drawBoardFrame, drawBoardState } from './drawBoard';
import useBoardInteraction from '../hooks/useBoardInteraction';

const BOARD_ASPECT = 13.6 / 7;

function measureCanvasSize(container) {
  const w = Math.max(1, Math.floor(container.clientWidth));
  let h = Math.floor(container.clientHeight);

  if (h >= 50) {
    return { w, h };
  }

  const slot = container.closest('.room-board');
  const slotW = slot ? Math.floor(slot.clientWidth) : w;
  const slotH = slot ? Math.floor(slot.clientHeight) : 0;
  const width = Math.max(1, w || slotW);
  const byAspect = Math.floor((width * BOARD_ASPECT));
  const hFromSlot = slotH > 0 ? Math.min(byAspect, slotH) : byAspect;

  return { w: width, h: Math.max(1, hFromSlot) };
}

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
  const lastSizeRef = useRef({ w: 0, h: 0 });
  const paintStateRef = useRef({});

  paintStateRef.current = {
    board,
    moveFrom,
    highlightedEssential,
    highlightedCaptured,
    capturedGhostPieces,
    lastMove,
    historyFrom,
    historyTo,
  };

  const resolveCellAt = useCallback((clientX, clientY) => {
    const canvas = canvasRef.current;
    const layout = layoutRef.current;
    if (!canvas || !layout) return null;
    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return hitTestCell(layout.cells, x, y);
  }, []);

  const {
    beginDrag,
    handleCellClick,
    registerDragGhostListener,
    dragGhostRef,
  } = useBoardInteraction({
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

    const state = paintStateRef.current;
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
      ...state,
      dragGhost,
    });
  }, []);

  const paintRef = useRef(paint);
  paintRef.current = paint;

  const schedulePaint = useCallback(() => {
    if (rafRef.current != null) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      paintRef.current();
    });
  }, []);

  const resizeCanvas = useCallback(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const { w, h } = measureCanvasSize(container);
    const sizeChanged = lastSizeRef.current.w !== w || lastSizeRef.current.h !== h;
    lastSizeRef.current = { w, h };

    if (sizeChanged) {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;

      const ctx = canvas.getContext('2d');
      if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      layoutRef.current = computeBoardLayout(myColor, w, h);
    }

    schedulePaint();
  }, [myColor, schedulePaint]);

  useEffect(() => {
    resizeCanvas();
    const container = containerRef.current;
    const slot = container?.closest('.room-board');
    const observeTarget = slot ?? container;
    const ro = typeof ResizeObserver !== 'undefined' && observeTarget
      ? new ResizeObserver(resizeCanvas)
      : null;
    if (observeTarget) ro?.observe(observeTarget);
    window.addEventListener('resize', resizeCanvas);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', resizeCanvas);
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, [resizeCanvas]);

  useEffect(() => {
    schedulePaint();
  }, [
    board,
    moveFrom,
    highlightedEssential,
    highlightedCaptured,
    capturedGhostPieces,
    lastMove,
    historyFrom,
    historyTo,
    schedulePaint,
  ]);

  useEffect(() => {
    const onGhost = (ghost) => {
      dragGhostDrawRef.current = ghost;
      schedulePaint();
    };
    return registerDragGhostListener(onGhost);
  }, [registerDragGhostListener, schedulePaint]);

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
