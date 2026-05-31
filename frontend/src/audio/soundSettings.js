const ENABLED_KEY = 'shatra_sound_enabled';
const VOLUME_KEY = 'shatra_sound_volume';
const DEFAULT_VOLUME = 0.5;

export function isSoundEnabled() {
  try {
    const raw = localStorage.getItem(ENABLED_KEY);
    if (raw === null) return true;
    return raw === 'true';
  } catch {
    return true;
  }
}

export function setSoundEnabled(enabled) {
  try {
    localStorage.setItem(ENABLED_KEY, enabled ? 'true' : 'false');
  } catch {
    /* ignore */
  }
}

export function getSoundVolume() {
  try {
    const raw = parseFloat(localStorage.getItem(VOLUME_KEY));
    if (!Number.isFinite(raw)) return DEFAULT_VOLUME;
    return Math.min(1, Math.max(0, raw));
  } catch {
    return DEFAULT_VOLUME;
  }
}

export function setSoundVolume(volume) {
  try {
    localStorage.setItem(VOLUME_KEY, String(Math.min(1, Math.max(0, volume))));
  } catch {
    /* ignore */
  }
}

export function getEffectiveVolume() {
  return isSoundEnabled() ? getSoundVolume() : 0;
}
