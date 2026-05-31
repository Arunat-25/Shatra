import { getEffectiveVolume } from './soundSettings';
import { getAudioContext, resumeAudioContext } from './audioContext';
import { SOUND_MANIFEST, soundUrl } from './soundManifest';

/** @type {Map<string, AudioBuffer>} */
const bufferCache = new Map();
let preloadPromise = null;

async function fetchBuffer(filename) {
  const cached = bufferCache.get(filename);
  if (cached) return cached;

  const audio = getAudioContext();
  if (!audio) return null;

  const res = await fetch(soundUrl(filename));
  if (!res.ok) throw new Error(`sound fetch failed: ${filename} (${res.status})`);

  const data = await res.arrayBuffer();
  const buffer = await audio.decodeAudioData(data.slice(0));
  bufferCache.set(filename, buffer);
  return buffer;
}

function pickFile(entry) {
  const { files } = entry;
  if (files.length === 1) return files[0];
  return files[Math.floor(Math.random() * files.length)];
}

/**
 * Preload all manifest sounds (call after user gesture).
 * @returns {Promise<void>}
 */
export async function preloadGameSounds() {
  if (preloadPromise) return preloadPromise;
  preloadPromise = (async () => {
    await resumeAudioContext();
    const names = new Set();
    for (const entry of Object.values(SOUND_MANIFEST)) {
      for (const f of entry.files) names.add(f);
    }
    await Promise.all([...names].map((name) => fetchBuffer(name).catch(() => null)));
  })();
  return preloadPromise;
}

/**
 * @param {keyof typeof SOUND_MANIFEST} key
 * @param {number} [volume] 0–1 user volume multiplier
 * @returns {Promise<boolean>} true if sample played
 */
export async function playSample(key, volume) {
  const vol = volume ?? getEffectiveVolume();
  if (vol <= 0) return false;

  const entry = SOUND_MANIFEST[key];
  if (!entry) return false;

  const audio = getAudioContext();
  if (!audio) return false;

  try {
    await resumeAudioContext();
    const filename = pickFile(entry);
    const buffer = await fetchBuffer(filename);
    if (!buffer) return false;

    const gainValue = vol * (entry.gain ?? 1);
    const source = audio.createBufferSource();
    const gain = audio.createGain();
    source.buffer = buffer;
    gain.gain.value = gainValue;
    source.connect(gain);
    gain.connect(audio.destination);
    source.start(0);
    return true;
  } catch {
    return false;
  }
}

/** @param {keyof typeof SOUND_MANIFEST} key */
export function playSampleSync(key, volume) {
  void playSample(key, volume);
}
