import { useCallback, useEffect, useRef, useState } from 'react';

export const TUTORIAL_SLIDE_COUNT = 4;
export const TUTORIAL_INTERVAL_MS = 6000;

function prefersReducedMotion() {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export default function useTutorialCarousel(slideCount = TUTORIAL_SLIDE_COUNT) {
  const [index, setIndex] = useState(0);
  const pausedRef = useRef(false);
  const timerRef = useRef(null);
  const reducedMotionRef = useRef(prefersReducedMotion());

  const next = useCallback(() => {
    setIndex((i) => (i + 1) % slideCount);
  }, [slideCount]);

  const clearTimer = useCallback(() => {
    if (timerRef.current != null) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const startTimer = useCallback(() => {
    clearTimer();
    if (reducedMotionRef.current || pausedRef.current) return;
    timerRef.current = setInterval(() => {
      if (!pausedRef.current) {
        setIndex((i) => (i + 1) % slideCount);
      }
    }, TUTORIAL_INTERVAL_MS);
  }, [clearTimer, slideCount]);

  useEffect(() => {
    startTimer();
    return clearTimer;
  }, [index, startTimer, clearTimer]);

  const onPointerDown = useCallback(() => {
    pausedRef.current = true;
    clearTimer();
  }, [clearTimer]);

  const onPointerUp = useCallback(() => {
    pausedRef.current = false;
    startTimer();
  }, [startTimer]);

  const onClick = useCallback(() => {
    next();
  }, [next]);

  const goTo = useCallback((slideIndex) => {
    setIndex(slideIndex % slideCount);
  }, [slideCount]);

  return {
    index,
    next,
    goTo,
    onPointerDown,
    onPointerUp,
    onPointerCancel: onPointerUp,
    onPointerLeave: onPointerUp,
    onClick,
  };
}
