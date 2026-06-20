import { useEffect } from 'react';
import { isDevProbeEnabled } from '../debug/devProbe';

/**
 * Run a layout probe on mount/deps change and on window resize (dev only).
 * @param {() => void} probeFn
 * @param {unknown[]} deps
 */
export default function useDevLayoutProbe(probeFn, deps = []) {
  useEffect(() => {
    if (!isDevProbeEnabled()) return undefined;

    const run = () => probeFn();
    run();
    const tId = window.setTimeout(run, 150);
    window.addEventListener('resize', run);
    return () => {
      window.clearTimeout(tId);
      window.removeEventListener('resize', run);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- probe deps are caller-controlled
  }, deps);
}
