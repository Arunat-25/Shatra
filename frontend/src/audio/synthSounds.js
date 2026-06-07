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

/** Short wooden board tap: low thump + filtered contact click. */
function playBoardTap({ volume, intensity = 1, pitch = 1 }) {
  const vol = volume ?? getEffectiveVolume();
  if (vol <= 0) return;

  const audio = getAudioContext();
  if (!audio) return;

  const now = audio.currentTime;
  const amp = 0.24 * intensity * vol;

  const thump = audio.createOscillator();
  const thumpGain = audio.createGain();
  thump.type = 'sine';
  thump.frequency.setValueAtTime(165 * pitch, now);
  thump.frequency.exponentialRampToValueAtTime(Math.max(72 * pitch, 1), now + 0.045);
  thumpGain.gain.setValueAtTime(0.0001, now);
  thumpGain.gain.exponentialRampToValueAtTime(Math.max(amp, 0.0001), now + 0.004);
  thumpGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.075);
  thump.connect(thumpGain);
  thumpGain.connect(audio.destination);
  thump.start(now);
  thump.stop(now + 0.09);

  const clickLen = Math.floor(audio.sampleRate * 0.018);
  const clickBuffer = audio.createBuffer(1, clickLen, audio.sampleRate);
  const clickData = clickBuffer.getChannelData(0);
  for (let i = 0; i < clickLen; i += 1) {
    clickData[i] = (Math.random() * 2 - 1) * (1 - i / clickLen) ** 1.6;
  }
  const click = audio.createBufferSource();
  click.buffer = clickBuffer;
  const filter = audio.createBiquadFilter();
  filter.type = 'bandpass';
  filter.frequency.value = 950 * pitch;
  filter.Q.value = 0.9;
  const clickGain = audio.createGain();
  clickGain.gain.setValueAtTime(0.14 * intensity * vol, now);
  clickGain.gain.exponentialRampToValueAtTime(0.0001, now + 0.014);
  click.connect(filter);
  filter.connect(clickGain);
  clickGain.connect(audio.destination);
  click.start(now);
}

export function playMove(volume) {
  playBoardTap({ volume, intensity: 1, pitch: 1 });
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
  playBoardTap({ volume, intensity: 0.45, pitch: 1.18 });
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
  playSequence([
    {
      frequency: 932,
      frequencyEnd: 740,
      duration: 0.18,
      type: 'square',
      peakGain: 0.13,
      gap: 80,
    },
    {
      frequency: 622,
      frequencyEnd: 494,
      duration: 0.24,
      type: 'square',
      peakGain: 0.11,
    },
  ], volume);
}
