import { useCallback, useEffect, useRef, useState } from 'react';
import { runSlideAnimation, slideDurationMs } from '../board/slideAnimation';

/**
 * Slide overlay for confirmed moves (click or opponent). Drag drops mark handled
 * via markSlideHandled to avoid double animation.
 */
export default function usePieceSlideOverlay({
  lastMove,
  board,
  getCellCenter,
  enabled = true,
}) {
  const [overlay, setOverlay] = useState(null);
  const skipKeyRef = useRef(null);
  const cancelAnimRef = useRef(null);
  const lastKeyRef = useRef('');

  const markSlideHandled = useCallback((from, to) => {
    skipKeyRef.current = `${from}-${to}`;
  }, []);

  const startSlide = useCallback(({
    piece,
    fromCell,
    toCell,
    fromX,
    fromY,
    toX,
    toY,
    size,
    onComplete,
  }) => {
    cancelAnimRef.current?.();
    setOverlay({
      piece,
      fromCell,
      toCell,
      x: fromX,
      y: fromY,
      size,
    });
    cancelAnimRef.current = runSlideAnimation({
      duration: slideDurationMs(),
      from: { x: fromX, y: fromY },
      to: { x: toX, y: toY },
      onFrame: (_t, x, y) => {
        setOverlay((prev) => (prev ? { ...prev, x, y } : null));
      },
      onComplete: () => {
        setOverlay(null);
        cancelAnimRef.current = null;
        onComplete?.();
      },
    });
  }, []);

  useEffect(() => {
    if (!enabled || !lastMove?.from || !lastMove?.to) return undefined;

    const key = `${lastMove.from}-${lastMove.to}`;
    if (skipKeyRef.current === key) {
      skipKeyRef.current = null;
      lastKeyRef.current = key;
      return undefined;
    }
    if (lastKeyRef.current === key) return undefined;

    const piece = board[lastMove.to];
    if (!piece) return undefined;

    const from = getCellCenter?.(lastMove.from);
    const to = getCellCenter?.(lastMove.to);
    if (!from || !to) return undefined;

    lastKeyRef.current = key;
    startSlide({
      piece,
      fromCell: lastMove.from,
      toCell: lastMove.to,
      fromX: from.x,
      fromY: from.y,
      toX: to.x,
      toY: to.y,
      size: to.size ?? from.size,
    });

    return undefined;
  }, [lastMove, board, enabled, getCellCenter, startSlide]);

  useEffect(() => () => cancelAnimRef.current?.(), []);

  return { slideOverlay: overlay, startSlide, markSlideHandled };
}
