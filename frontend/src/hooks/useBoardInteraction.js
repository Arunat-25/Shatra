import { useCallback, useEffect, useRef } from 'react';
import { runSlideAnimation } from '../board/slideAnimation';
import { resolveSnapDrop } from '../board/resolveSnapDrop';

/**
 * Shared pointer click/drag for DOM and canvas boards.
 * @param {object} options
 * @param {() => number|null} options.resolveCellAt - map client coords to cell id
 * @param {Set<number>|number[]} [options.legalDests] - legal drop targets while dragging
 * @param {(cellId: number) => {x:number,y:number,size?:number}|null} [options.getCellCenter]
 * @param {(cellId: number) => {left:number,top:number,right:number,bottom:number}|null} [options.getCellBounds]
 * @param {(from: number, to: number) => void} [options.onDragDropComplete] - after slide-to-cell, before click handler
 * @param {(fromCell: number) => Iterable<number>} [options.getLegalDests] - sync legal targets at drag start
 */
export default function useBoardInteraction({
  board,
  onCellClick,
  moveFrom,
  interactive = true,
  enablePieceDrag = true,
  resolveCellAt,
  legalDests = null,
  getLegalDests = null,
  getCellCenter = null,
  getCellBounds = null,
  onDragDropComplete = null,
}) {
  const dragFromRef = useRef(null);
  const dragStartedAtRef = useRef(0);
  const dragStartPosRef = useRef(null);
  const dragLegalDestsRef = useRef(null);
  const activePointerIdRef = useRef(null);
  const ignoreClickUntilRef = useRef(0);
  const dragListenersRef = useRef(null);
  const dragGhostRef = useRef(null);
  const onDragGhostRef = useRef(null);
  const slideCancelRef = useRef(null);
  const pendingGhostPosRef = useRef(null);
  const ghostRafRef = useRef(null);

  const setDragGhost = useCallback((ghost) => {
    dragGhostRef.current = ghost;
    onDragGhostRef.current?.(ghost);
  }, []);

  const registerDragGhostListener = useCallback((listener) => {
    onDragGhostRef.current = listener;
    return () => {
      if (onDragGhostRef.current === listener) {
        onDragGhostRef.current = null;
      }
    };
  }, []);

  const clearDragListeners = useCallback(() => {
    const listeners = dragListenersRef.current;
    if (!listeners) return;
    window.removeEventListener('pointermove', listeners.onMove);
    window.removeEventListener('pointerup', listeners.onFinish);
    window.removeEventListener('pointercancel', listeners.onFinish);
    dragListenersRef.current = null;
  }, []);

  const isLegalDest = useCallback((cellId, dests = dragLegalDestsRef.current ?? legalDests) => {
    if (cellId == null || !dests) return false;
    if (dests instanceof Set) return dests.has(cellId);
    return dests.includes(cellId);
  }, [legalDests]);

  const scheduleGhostMove = useCallback((x, y) => {
    pendingGhostPosRef.current = { x, y };
    if (ghostRafRef.current != null) return;
    ghostRafRef.current = requestAnimationFrame(() => {
      ghostRafRef.current = null;
      const pos = pendingGhostPosRef.current;
      const ghost = dragGhostRef.current;
      if (ghost && pos) {
        setDragGhost({ ...ghost, x: pos.x, y: pos.y });
      }
    });
  }, [setDragGhost]);

  const animateGhostTo = useCallback((x, y, onDone) => {
    const ghost = dragGhostRef.current;
    if (!ghost) {
      onDone?.();
      return;
    }
    slideCancelRef.current?.();
    slideCancelRef.current = runSlideAnimation({
      from: { x: ghost.x, y: ghost.y },
      to: { x, y },
      onFrame: (_t, nx, ny) => {
        const current = dragGhostRef.current;
        if (current) setDragGhost({ ...current, x: nx, y: ny });
      },
      onComplete: () => {
        slideCancelRef.current = null;
        setDragGhost(null);
        onDone?.();
      },
    });
  }, [setDragGhost]);

  const finishDrag = useCallback((event) => {
    if (activePointerIdRef.current != null && event.pointerId !== activePointerIdRef.current) {
      return;
    }

    clearDragListeners();

    const from = dragFromRef.current;
    dragFromRef.current = null;
    activePointerIdRef.current = null;
    const activeLegalDests = dragLegalDestsRef.current ?? legalDests;
    dragLegalDestsRef.current = null;

    if (from == null) {
      setDragGhost(null);
      return;
    }

    const start = dragStartPosRef.current;
    dragStartPosRef.current = null;
    const moved = start
      ? Math.hypot(event.clientX - start.x, event.clientY - start.y)
      : 0;
    if (moved < 2) {
      setDragGhost(null);
      return;
    }

    const ghost = dragGhostRef.current;
    const targetCellId = resolveSnapDrop({
      clientX: event.clientX,
      clientY: event.clientY,
      from,
      legalDests: activeLegalDests,
      resolveCellAt,
      getCellCenter,
      getCellBounds,
      ghost: ghost ? { x: ghost.x, y: ghost.y, size: ghost.size } : null,
    });
    const canSlide = Boolean(getCellCenter);

    if (
      targetCellId != null
      && from !== targetCellId
      && isLegalDest(targetCellId, activeLegalDests)
      && canSlide
    ) {
      const center = getCellCenter(targetCellId);
      if (center) {
        ignoreClickUntilRef.current = Date.now() + 350;
        animateGhostTo(center.x, center.y, () => {
          onDragDropComplete?.(from, targetCellId);
          onCellClick(targetCellId);
        });
        return;
      }
    }

    if (canSlide) {
      const origin = getCellCenter(from);
      if (origin) {
        ignoreClickUntilRef.current = Date.now() + 350;
        animateGhostTo(origin.x, origin.y, () => {});
        return;
      }
    }

    setDragGhost(null);
  }, [
    clearDragListeners,
    onCellClick,
    resolveCellAt,
    setDragGhost,
    getCellCenter,
    getCellBounds,
    legalDests,
    isLegalDest,
    animateGhostTo,
    onDragDropComplete,
  ]);

  const beginDrag = useCallback((cellId, event, cellSize) => {
    if (!interactive || !enablePieceDrag) return;
    const piece = board[cellId];
    if (!piece || !event) return;
    if (event.button != null && event.button !== 0) return;

    event.preventDefault();
    clearDragListeners();
    slideCancelRef.current?.();

    dragFromRef.current = cellId;
    dragStartedAtRef.current = Date.now();
    dragStartPosRef.current = { x: event.clientX, y: event.clientY };
    activePointerIdRef.current = event.pointerId;
    ignoreClickUntilRef.current = Date.now() + 250;
    if (moveFrom !== cellId) {
      onCellClick(cellId);
    }

    const freshDests = getLegalDests?.(cellId);
    if (freshDests != null) {
      dragLegalDestsRef.current = freshDests instanceof Set
        ? freshDests
        : new Set(freshDests);
    } else if (legalDests != null) {
      dragLegalDestsRef.current = legalDests instanceof Set
        ? legalDests
        : new Set(legalDests);
    } else {
      dragLegalDestsRef.current = new Set();
    }

    setDragGhost({
      fromId: cellId,
      piece,
      x: event.clientX,
      y: event.clientY,
      size: cellSize,
    });

    const onMove = (e) => {
      if (e.pointerId !== event.pointerId) return;
      scheduleGhostMove(e.clientX, e.clientY);
    };

    const onFinish = (e) => {
      if (e.pointerId !== event.pointerId) return;
      finishDrag(e);
    };

    window.addEventListener('pointermove', onMove, { passive: true });
    window.addEventListener('pointerup', onFinish);
    window.addEventListener('pointercancel', onFinish);
    dragListenersRef.current = { onMove, onFinish };
  }, [
    board,
    interactive,
    enablePieceDrag,
    moveFrom,
    onCellClick,
    clearDragListeners,
    finishDrag,
    setDragGhost,
    scheduleGhostMove,
    getLegalDests,
    legalDests,
  ]);

  const handleCellClick = useCallback((cellId) => {
    if (!interactive) return;
    if (Date.now() < ignoreClickUntilRef.current) return;
    onCellClick(cellId);
  }, [interactive, onCellClick]);

  useEffect(() => () => {
    clearDragListeners();
    slideCancelRef.current?.();
    if (ghostRafRef.current != null) cancelAnimationFrame(ghostRafRef.current);
  }, [clearDragListeners]);

  return {
    beginDrag,
    handleCellClick,
    registerDragGhostListener,
    dragGhostRef,
  };
}
