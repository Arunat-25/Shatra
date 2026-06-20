import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/react';
import useDevLayoutProbe from './useDevLayoutProbe';
import { isDevProbeEnabled } from '../debug/devProbe';

vi.mock('../debug/devProbe', () => ({
  isDevProbeEnabled: vi.fn(),
}));

function ProbeHost({ probeFn, deps = [] }) {
  useDevLayoutProbe(probeFn, deps);
  return null;
}

describe('useDevLayoutProbe', () => {
  beforeEach(() => {
    vi.mocked(isDevProbeEnabled).mockReturnValue(false);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('does not run probe when dev probes disabled', () => {
    const probeFn = vi.fn();
    render(<ProbeHost probeFn={probeFn} deps={[1]} />);
    expect(probeFn).not.toHaveBeenCalled();
  });

  it('runs probe on mount when dev probes enabled', () => {
    vi.mocked(isDevProbeEnabled).mockReturnValue(true);
    const probeFn = vi.fn();
    render(<ProbeHost probeFn={probeFn} deps={[1]} />);
    expect(probeFn).toHaveBeenCalled();
  });
});
