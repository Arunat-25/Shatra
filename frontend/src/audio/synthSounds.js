import { getEffectiveVolume } from './soundSettings';
import { getAudioContext } from './audioContext';

export { resumeAudioContext } from './audioContext';

function playTone({
  frequency,
  duration = 0.08,
  type = 'sine',
  peakGain = 0.14,
  volume,
  frequencyEnd,
}) {
  const vol = volume ?? getEffectiveVolume();
  if (vol <= 0) return;

  const audio = getAudioContext();
  if (!audio) return;

  const now = audio.currentTime;
  const osc = audio.createOscillator();
  const gain = audio.createGain();

  osc.type = type;
  osc.frequency.setValueAtTime(frequency, now);
  if (frequencyEnd != null) {
    osc.frequency.exponentialRampToValueAtTime(
      Math.max(frequencyEnd, 1),
      now + duration,
    );
  }

  const amp = peakGain * vol;
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(Math.max(amp, 0.0001), now + 0.008);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

  osc.connect(gain);
  gain.connect(audio.destination);
  osc.start(now);
  osc.stop(now + duration + 0.02);
}

function playSequence(notes, volume) {
  const vol = volume ?? getEffectiveVolume();
  if (vol <= 0) return;
  let delay = 0;
  for (const note of notes) {
    const { gap = 0, ...opts } = note;
    setTimeout(() => playTone({ ...opts, volume: vol }), delay);
    delay += (opts.duration ?? 0.08) * 1000 + gap;
  }
}

export function playMove(volume) {
  playTone({ frequency: 520, duration: 0.05, peakGain: 0.1, volume });
}

export function playCapture(volume) {
  playTone({ frequency: 220, duration: 0.09, type: 'triangle', peakGain: 0.16, volume });
}

export function playGameStart(volume) {
  playSequence([
    { frequency: 392, duration: 0.07, gap: 20 },
    { frequency: 523, duration: 0.1, peakGain: 0.12 },
  ], volume);
}

export function playWin(volume) {
  playSequence([
    { frequency: 523, duration: 0.08, gap: 30 },
    { frequency: 659, duration: 0.08, gap: 30 },
    { frequency: 784, duration: 0.14, peakGain: 0.13 },
  ], volume);
}

export function playLoss(volume) {
  playSequence([
    { frequency: 330, duration: 0.12, frequencyEnd: 220, peakGain: 0.12, gap: 40 },
    { frequency: 196, duration: 0.18, peakGain: 0.1 },
  ], volume);
}

export function playDraw(volume) {
  playSequence([
    { frequency: 440, duration: 0.1, gap: 50 },
    { frequency: 440, duration: 0.1 },
  ], volume);
}

export function playSelect(volume) {
  playTone({ frequency: 680, duration: 0.03, peakGain: 0.06, volume });
}

export function playError(volume) {
  playTone({ frequency: 140, duration: 0.12, type: 'square', peakGain: 0.08, volume });
}

export function playChat(volume) {
  playTone({ frequency: 880, duration: 0.04, peakGain: 0.07, volume });
}

export function playDrawOffer(volume) {
  playSequence([
    { frequency: 600, duration: 0.06, gap: 40 },
    { frequency: 500, duration: 0.08, peakGain: 0.09 },
  ], volume);
}

export function playLowTime(volume) {
  playTone({ frequency: 740, duration: 0.06, type: 'triangle', peakGain: 0.11, volume });
}
