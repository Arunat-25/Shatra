/** Lichess lila piano set — paths under /sounds/piano/ */
export const SOUND_SET = 'piano';

export const SOUND_BASE = `/sounds/${SOUND_SET}`;

/** @typedef {{ files: string[], gain?: number }} SoundEntry */

/** @type {Record<string, SoundEntry>} */
export const SOUND_MANIFEST = {
  move: { files: ['Move.ogg'] },
  capture: { files: ['Capture.ogg'] },
  gameStart: { files: ['NewChallenge.ogg'] },
  win: { files: ['Victory.ogg'] },
  loss: { files: ['Defeat.ogg'] },
  draw: { files: ['Draw.ogg'] },
  select: { files: ['Move.ogg'], gain: 0.45 },
  chat: { files: ['GenericNotify.ogg'] },
  drawOffer: { files: ['NewPM.ogg'] },
  lowTime: { files: ['LowTime.ogg'] },
};

/** All unique filenames to preload. */
export function allSoundFiles() {
  const names = new Set();
  for (const entry of Object.values(SOUND_MANIFEST)) {
    for (const f of entry.files) names.add(f);
  }
  return [...names];
}

export function soundUrl(filename) {
  return `${SOUND_BASE}/${filename}`;
}
