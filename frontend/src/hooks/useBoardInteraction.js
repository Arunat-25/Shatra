import { useCallback, useEffect, useRef } from 'react';
import { runSlideAnimation } from '../board/slideAnimation';

/**
 * Shared pointer click/drag for DOM and canvas boards.
 * @param {object} options
 * @param {() => number|null} options.resolveCellAt - map client coords to cell id
 * @param {Set<number>|number[]} [options.legalDests] - legal drop targets while dragging
 * @param {(cellId: number) => {x:number,y:number,size?:number}|null} [options.getCellCenter]
 * @param {(from: number, to: number) => void} [options.onDragDropComplete] - after slide-to-cell, before click handler
 */
export default function useBoardInteraction({
  board,
  onCellClick,
  moveFrom,
  interactive = true,
  enablePieceDrag = true,
  resolveCellAt,
  legalDests = null,
  getCellCenter = null,
  onDragDropComplete = null,
}) {
  const dragFromRef = useRef(null);
  const dragStartedAtRef = useRef(0);
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

  const isLegalDest = useCallback((cellId) => {
    if (cellId == null || !legalDests) return false;
    if (legalDests instanceof Set) return legalDests.has(cellId);
    return legalDests.includes(cellId);
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

    if (from == null) {
      setDragGhost(null);
      return;
    }

    const elapsed = Date.now() - (dragStartedAtRef.current || 0);
    if (elapsed < 50) {
      setDragGhost(null);
      return;
    }

    const targetCellId = resolveCellAt(event.clientX, event.clientY);
    const canSlide = Boolean(getCellCenter);

    if (
      targetCellId != null
      && from !== targetCellId
      && isLegalDest(targetCellId)
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
    activePointerIdRef.current = event.pointerId;
    ignoreClickUntilRef.current = Date.now() + 250;
    if (moveFrom !== cellId) {
      onCellClick(cellId);
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
