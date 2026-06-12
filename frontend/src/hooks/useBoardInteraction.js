import { useCallback, useEffect, useRef } from 'react';

/**
 * Shared pointer click/drag for DOM and canvas boards.
 * @param {object} options
 * @param {() => number|null} options.resolveCellAt - map client coords to cell id
 */
export default function useBoardInteraction({
  board,
  onCellClick,
  moveFrom,
  interactive = true,
  enablePieceDrag = true,
  resolveCellAt,
}) {
  const dragFromRef = useRef(null);
  const dragStartedAtRef = useRef(0);
  const activePointerIdRef = useRef(null);
  const ignoreClickUntilRef = useRef(0);
  const dragListenersRef = useRef(null);
  const dragGhostRef = useRef(null);
  const onDragGhostRef = useRef(null);

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

    const targetCellId = resolveCellAt(event.clientX, event.clientY);
    if (targetCellId != null && from !== targetCellId) {
      ignoreClickUntilRef.current = Date.now() + 250;
      onCellClick(targetCellId);
    }
  }, [clearDragListeners, onCellClick, resolveCellAt, setDragGhost]);

  const beginDrag = useCallback((cellId, event, cellSize) => {
    if (!interactive || !enablePieceDrag) return;
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

    setDragGhost({
      fromId: cellId,
      piece,
      x: event.clientX,
      y: event.clientY,
      size: cellSize,
    });

    const onMove = (e) => {
      if (e.pointerId !== event.pointerId) return;
      const ghost = dragGhostRef.current;
      if (ghost) {
        setDragGhost({ ...ghost, x: e.clientX, y: e.clientY });
      }
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
  ]);

  const handleCellClick = useCallback((cellId) => {
    if (!interactive) return;
    if (Date.now() < ignoreClickUntilRef.current) return;
    onCellClick(cellId);
  }, [interactive, onCellClick]);

  useEffect(() => () => clearDragListeners(), [clearDragListeners]);

  return {
    beginDrag,
    handleCellClick,
    registerDragGhostListener,
    dragGhostRef,
  };
}
