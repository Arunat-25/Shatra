/** Game sound files under /sounds/piano/ */
export const SOUND_SET = 'piano';

export const SOUND_BASE = `/sounds/${SOUND_SET}`;

/** @typedef {{ files: string[], gain?: number }} SoundEntry */

/** @type {Record<string, SoundEntry>} */
export const SOUND_MANIFEST = {
  move: { files: ['Move.ogg'] },
  capture: { files: ['Capture.ogg'] },
  gameStart: { files: ['GameEvent.ogg'] },
  win: { files: ['GameEvent.ogg'] },
  loss: { files: ['GameEvent.ogg'] },
  draw: { files: ['GameEvent.ogg'] },
  chat: { files: ['GenericNotify.ogg'] },
  drawOffer: { files: ['GenericNotify.ogg'] },
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
