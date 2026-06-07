import { describe, expect, it } from 'vitest';
import { shouldRequestChainHints } from './chainCaptureHints';

describe('shouldRequestChainHints', () => {
  const base = {
    waiting: false,
    gameOver: false,
    viewingHistoryIndex: null,
    moversColor: 'белый',
    myColor: 'белый',
    posForMandatoryCapture: 19,
    highlightedEssential: [],
    board: { 19: 'белый бий' },
  };

  it('requests hints during active chain without highlights', () => {
    expect(shouldRequestChainHints(base)).toBe(true);
  });

  it('skips when highlights already present', () => {
    expect(shouldRequestChainHints({ ...base, highlightedEssential: [33] })).toBe(false);
  });

  it('skips when chain is not active', () => {
    expect(shouldRequestChainHints({ ...base, posForMandatoryCapture: null })).toBe(false);
  });

  it('skips when not my turn', () => {
    expect(shouldRequestChainHints({ ...base, myColor: 'черный' })).toBe(false);
  });
});
