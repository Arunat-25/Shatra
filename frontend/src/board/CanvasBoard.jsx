import { useCallback, useEffect, useMemo, useRef } from 'react';
import useMediaQuery from '../hooks/useMediaQuery';
import { COMPACT_GAME_QUERY } from '../constants';
import {
  computeBoardLayout,
  hitTestCell,
  layoutDrawScale,
  readBoardUnitMetrics,
  readCellNumberScale,
  readBoardHeightUnits,
  deriveMetricsFromBoardSlot,
  BOARD_HEIGHT_UNITS,
} from './layoutMetrics';
import { drawBoardFrame, drawBoardState } from './drawBoard';
import useBoardInteraction from '../hooks/useBoardInteraction';
import usePieceSlideOverlay from '../hooks/usePieceSlideOverlay';

const BOARD_ASPECT = 7 / BOARD_HEIGHT_UNITS;

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
    cellSize: Math.max(0, Math.min(
      h / (readBoardHeightUnits(boardEl) || BOARD_HEIGHT_UNITS),
      w / 7,
    )),
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
  const compactViewport = useMediaQuery(COMPACT_GAME_QUERY);
  const fillSlotRef = useRef(compactViewport);
  fillSlotRef.current = compactViewport;
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
    const scale = layoutDrawScale(layout, cr.width, cr.height, fillSlotRef.current);
    return {
      x: cr.left + scale.offsetX + (rect.x + rect.w / 2) * scale.x,
      y: cr.top + scale.offsetY + (rect.y + rect.h / 2) * scale.y,
      size: rect.w * scale.x,
    };
  }, []);

  const getCellBounds = useCallback((cellId) => {
    const layout = layoutRef.current;
    const canvas = canvasRef.current;
    const rect = layout?.cells?.[cellId];
    if (!rect || !canvas) return null;
    const cr = canvas.getBoundingClientRect();
    const scale = layoutDrawScale(layout, cr.width, cr.height, fillSlotRef.current);
    return {
      left: cr.left + scale.offsetX + rect.x * scale.x,
      top: cr.top + scale.offsetY + rect.y * scale.y,
      right: cr.left + scale.offsetX + (rect.x + rect.w) * scale.x,
      bottom: cr.top + scale.offsetY + (rect.y + rect.h) * scale.y,
    };
  }, []);

  const resolveCellAt = useCallback((clientX, clientY) => {
    const canvas = canvasRef.current;
    const layout = layoutRef.current;
    if (!canvas || !layout) return null;
    const rect = canvas.getBoundingClientRect();
    const scale = layoutDrawScale(layout, rect.width, rect.height, fillSlotRef.current);
    const x = (clientX - rect.left - scale.offsetX) / (scale.x || 1);
    const y = (clientY - rect.top - scale.offsetY) / (scale.y || 1);
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
    const displayW = canvas.clientWidth || layout.width;
    const displayH = canvas.clientHeight || layout.contentHeight;
    const scale = layoutDrawScale(layout, displayW, displayH, fillSlotRef.current);
    ctx.setTransform(
      dpr * scale.x,
      0,
      0,
      dpr * scale.y,
      dpr * scale.offsetX,
      dpr * scale.offsetY,
    );

    drawBoardFrame(ctx, layout, drawTheme, myColor);

    const boardEl = containerRef.current?.closest?.('.board');
    const cellNumberScale = readCellNumberScale(boardEl);

    const hiddenPieceCells = new Set();
    if (slideOverlayDrawRef.current?.toCell != null) {
      hiddenPieceCells.add(slideOverlayDrawRef.current.toCell);
    }

    drawBoardState(ctx, layout, {
      ...state,
      dragGhost: dragGhostDrawRef.current,
      slideOverlay: slideOverlayDrawRef.current,
      hiddenPieceCells,
      showCellNumbers: true,
      cellNumberScale,
      theme: drawTheme,
      vectorOnlySprites,
    });
  }, [drawTheme, vectorOnlySprites, myColor]);

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

    const fillSlot = fillSlotRef.current;
    const { w: layoutW, h: layoutH, layout } = measureCanvasLayout(container, myColor);
    layoutRef.current = layout;

    let w;
    let h;
    if (fillSlot) {
      container.style.width = '100%';
      container.style.height = '100%';
      const cr = container.getBoundingClientRect();
      w = Math.max(1, Math.floor(cr.width));
      h = Math.max(1, Math.floor(cr.height));
    } else {
      w = layoutW;
      h = layoutH;
      container.style.width = `${w}px`;
      container.style.height = `${h}px`;
    }

    const sizeChanged = lastSizeRef.current.w !== w || lastSizeRef.current.h !== h;
    lastSizeRef.current = { w, h };

    if (sizeChanged || canvas.width !== Math.floor(w * (window.devicePixelRatio || 1))) {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
    }

    const scale = layoutDrawScale(layout, w, h, fillSlot);
    if (canvas && layout) {
      canvas.dataset.scaleX = String(scale.x);
      canvas.dataset.scaleY = String(scale.y);
      canvas.dataset.scaleRatio = scale.y > 0 ? String(scale.x / scale.y) : '1';
      const cell = layout.cells?.[25];
      if (cell) {
        canvas.dataset.cellRenderW = String(cell.w * scale.x);
        canvas.dataset.cellRenderH = String(cell.h * scale.y);
      }
    }

    schedulePaint();
  }, [myColor, schedulePaint, compactViewport]);

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
