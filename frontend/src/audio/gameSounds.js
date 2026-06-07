import { getEffectiveVolume } from './soundSettings';
import { playSample } from './sampleSounds';
import * as synth from './synthSounds';

function vol(override) {
  return override ?? getEffectiveVolume();
}

async function play(key, volume, synthFn) {
  const v = vol(volume);
  if (v <= 0) return;
  const ok = await playSample(key, v);
  if (!ok && synthFn) synthFn(v);
}

export function playMove(volume) {
  void play('move', volume, synth.playMove);
}

export function playCapture(volume) {
  void play('capture', volume, synth.playCapture);
}

export function playGameStart(volume) {
  void play('gameStart', volume, synth.playGameStart);
}

export function playWin(volume) {
  void play('win', volume, synth.playWin);
}

export function playLoss(volume) {
  void play('loss', volume, synth.playLoss);
}

export function playDraw(volume) {
  void play('draw', volume, synth.playDraw);
}

export function playError(volume) {
  void play('error', volume, synth.playError);
}

export function playChat(volume) {
  void play('chat', volume, synth.playChat);
}

export function playDrawOffer(volume) {
  void play('drawOffer', volume, synth.playDrawOffer);
}

export function playLowTime(volume) {
  const v = vol(volume);
  if (v <= 0) return;
  synth.playLowTime(v);
}

export { preloadGameSounds } from './sampleSounds';
export { resumeAudioContext } from './audioContext';
