import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('./soundSettings', () => ({
  getEffectiveVolume: vi.fn(() => 0.5),
}));

const mockDecode = vi.fn();
const mockResume = vi.fn().mockResolvedValue(undefined);
const mockStart = vi.fn();
const mockConnect = vi.fn();

vi.mock('./audioContext', () => ({
  getAudioContext: vi.fn(() => ({
    decodeAudioData: mockDecode,
    createBufferSource: () => ({ connect: mockConnect, start: mockStart, buffer: null }),
    createGain: () => ({ connect: mockConnect, gain: { value: 0 } }),
    destination: {},
  })),
  resumeAudioContext: (...args) => mockResume(...args),
}));

import { getEffectiveVolume } from './soundSettings';
import { playSample } from './sampleSounds';

describe('sampleSounds', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getEffectiveVolume.mockReturnValue(0.5);
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)),
    });
    mockDecode.mockResolvedValue({ duration: 0.1 });
  });

  it('does not play when volume is zero', async () => {
    getEffectiveVolume.mockReturnValue(0);
    const ok = await playSample('move');
    expect(ok).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('fetches and plays move sample', async () => {
    const ok = await playSample('move', 0.8);
    expect(ok).toBe(true);
    expect(global.fetch).toHaveBeenCalledWith('/sounds/piano/Move.ogg');
    expect(mockStart).toHaveBeenCalled();
  });
});
