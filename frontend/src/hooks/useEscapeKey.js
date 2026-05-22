import { useEffect } from 'react';

/**
 * Хук для обработки нажатия Escape.
 * @param {boolean} active — условие, при котором хук активен
 * @param {function} onEscape — колбэк при нажатии Escape
 */
export default function useEscapeKey(active, onEscape) {
  useEffect(() => {
    if (!active) return;
    const handler = (e) => {
      if (e.key === 'Escape') onEscape();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [active, onEscape]);
}