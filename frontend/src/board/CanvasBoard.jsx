import { useCallback, useEffect, useMemo, useRef } from 'react';
import { COMPACT_GAME_QUERY } from '../constants';
import useMediaQuery from '../hooks/useMediaQuery';
import { computeBoardLayout, hitTestCell, readBoardUnitMetrics, deriveMetricsFromBoardSlot } from './layoutMetrics';
import { drawBoardFrame, drawBoardState } from './drawBoard';
import useBoardInteraction from '../hooks/useBoardInteraction';
import usePieceSlideOverlay from '../hooks/usePieceSlideOverlay';

const BOARD_ASPECT = 7 / 13.6;

function measureCanvasLayout(container, myColor) {
  const boardEl = container?.closest?.('.board');
  const metrics = readBoardUnitMetrics(boardEl) || deriveMetricsFromBoardSlot(boardEl);
  if (metrics) {
    const layout = computeBoardLayout(myColor, metrics);
    return {
      w: Math.max(1, Math.ceil(layout.width)),
      h: Math.max(1, Math.ceil(layout.contentHeight)),
      layout,
    };
  }

  const w = Math.max(1, Math.floor(container.clientWidth));
  let h = Math.floor(container.clientHeight);
  if (h < 50) {
    const slot = container.closest('.room-board');
    const slotW = slot ? Math.floor(slot.clientWidth) : w;
    const slotH = slot ? Math.floor(slot.clientHeight) : 0;
    const width = Math.max(1, w || slotW);
    const byAspect = Math.floor(width * BOARD_ASPECT);
    h = slotH > 0 ? Math.min(byAspect, slotH) : byAspect;
  }

  const fallbackMetrics = {
    cellSize: Math.max(0, Math.min((h - 20) / 13.6, (w - 20) / 7)),
    reserveSize: 0,
  };
  fallbackMetrics.reserveSize = fallbackMetrics.cellSize * 0.86;
  const layout = computeBoardLayout(myColor, fallbackMetrics);

  return {
    w: Math.max(1, Math.ceil(layout.width)),
    h: Math.max(1, Math.ceil(layout.contentHeight)),
    layout,
  };
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
  enableMoveAnimation = true,
  drawTheme = 'default',
  vectorOnlySprites = false,
  getDragLegalDests = null,
}) {
  const isCompactViewport = useMediaQuery(COMPACT_GAME_QUERY);
  const showCellNumbers = !isCompactViewport;
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const layoutRef = useRef(null);
  const rafRef = useRef(null);
  const dragGhostDrawRef = useRef(null);
  const slideOverlayDrawRef = useRef(null);
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

  const getCellCenter = useCallback((cellId) => {
    const layout = layoutRef.current;
    const canvas = canvasRef.current;
    const rect = layout?.cells?.[cellId];
    if (!rect || !canvas) return null;
    const cr = canvas.getBoundingClientRect();
    return {
      x: cr.left + rect.x + rect.w / 2,
      y: cr.top + rect.y + rect.h / 2,
      size: rect.w,
    };
  }, []);

  const getCellBounds = useCallback((cellId) => {
    const layout = layoutRef.current;
    const canvas = canvasRef.current;
    const rect = layout?.cells?.[cellId];
    if (!rect || !canvas) return null;
    const cr = canvas.getBoundingClientRect();
    return {
      left: cr.left + rect.x,
      top: cr.top + rect.y,
      right: cr.left + rect.x + rect.w,
      bottom: cr.top + rect.y + rect.h,
    };
  }, []);

  const resolveCellAt = useCallback((clientX, clientY) => {
    const canvas = canvasRef.current;
    const layout = layoutRef.current;
    if (!canvas || !layout) return null;
    const rect = canvas.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return hitTestCell(layout.cells, x, y);
  }, []);

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
    enablePieceDrag: true,
    resolveCellAt,
    legalDests,
    getLegalDests: getDragLegalDests,
    getCellCenter,
    getCellBounds,
    onDragDropComplete,
  });

  const toCanvasOverlay = useCallback((overlay) => {
    if (!overlay?.piece) return null;
    const canvas = canvasRef.current;
    if (!canvas) return overlay;
    const cr = canvas.getBoundingClientRect();
    return {
      ...overlay,
      x: overlay.x - cr.left,
      y: overlay.y - cr.top,
    };
  }, []);

  const paint = useCallback(() => {
    const canvas = canvasRef.current;
    const layout = layoutRef.current;
    if (!canvas || !layout) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const state = paintStateRef.current;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.restore();

    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    drawBoardFrame(ctx, layout, drawTheme, myColor);

    const hiddenPieceCells = new Set();
    if (slideOverlayDrawRef.current?.toCell != null) {
      hiddenPieceCells.add(slideOverlayDrawRef.current.toCell);
    }

    drawBoardState(ctx, layout, {
      ...state,
      dragGhost: dragGhostDrawRef.current,
      slideOverlay: slideOverlayDrawRef.current,
      hiddenPieceCells,
      showCellNumbers,
      theme: drawTheme,
      vectorOnlySprites,
    });
  }, [drawTheme, vectorOnlySprites, showCellNumbers, myColor]);

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

    const { w, h, layout } = measureCanvasLayout(container, myColor);
    const sizeChanged = lastSizeRef.current.w !== w || lastSizeRef.current.h !== h;
    lastSizeRef.current = { w, h };

    container.style.width = `${w}px`;
    container.style.height = `${h}px`;

    if (sizeChanged || !layoutRef.current) {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      layoutRef.current = layout;
    }

    schedulePaint();
  }, [myColor, schedulePaint]);

  useEffect(() => {
    resizeCanvas();
    const container = containerRef.current;
    const boardEl = container?.closest('.board');
    const slot = container?.closest('.room-board');
    const observeTarget = boardEl ?? slot ?? container;
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
    slideOverlay,
    showCellNumbers,
    schedulePaint,
  ]);

  useEffect(() => {
    slideOverlayDrawRef.current = toCanvasOverlay(slideOverlay);
    schedulePaint();
  }, [slideOverlay, toCanvasOverlay, schedulePaint]);

  useEffect(() => registerDragGhostListener((ghost) => {
    dragGhostDrawRef.current = toCanvasOverlay(ghost);
    schedulePaint();
  }), [registerDragGhostListener, schedulePaint, toCanvasOverlay]);

  const onPointerDown = useCallback((event) => {
    if (!interactive) return;
    if (event.button != null && event.button !== 0) return;
    const cellId = resolveCellAt(event.clientX, event.clientY);
    if (cellId == null) return;

    const piece = board[cellId];
    if (piece) {
      const layout = layoutRef.current;
      const rect = layout?.cells?.[cellId];
      const cellSize = rect ? Math.round(rect.w) : 40;
      event.preventDefault();
      beginDrag(cellId, event, cellSize);
      schedulePaint();
      return;
    }

    event.preventDefault();
    handleCellClick(cellId);
    schedulePaint();
  }, [interactive, board, resolveCellAt, beginDrag, handleCellClick, schedulePaint]);

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
