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

  it('still requests hints during chain even if highlights are stale', () => {
    expect(shouldRequestChainHints({ ...base, highlightedEssential: [33] })).toBe(true);
  });

  it('skips when chain is not active', () => {
    expect(shouldRequestChainHints({ ...base, posForMandatoryCapture: null })).toBe(false);
  });

  it('skips when not my turn', () => {
    expect(shouldRequestChainHints({ ...base, myColor: 'черный' })).toBe(false);
  });

  it('skips while waiting for opponent', () => {
    expect(shouldRequestChainHints({ ...base, waiting: true })).toBe(false);
  });

  it('skips after game over', () => {
    expect(shouldRequestChainHints({ ...base, gameOver: true })).toBe(false);
  });

  it('skips when browsing move history', () => {
    expect(shouldRequestChainHints({ ...base, viewingHistoryIndex: 2 })).toBe(false);
  });

  it('skips when it is my turn but chain flag is off', () => {
    expect(shouldRequestChainHints({
      ...base,
      moversColor: 'белый',
      myColor: 'белый',
      posForMandatoryCapture: null,
    })).toBe(false);
  });
});
