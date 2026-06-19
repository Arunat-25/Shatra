const LITE_UI_KEY = 'shatra_lite_ui';

export function isLiteUiEnabled() {
  try {
    const raw = localStorage.getItem(LITE_UI_KEY);
    if (raw === null) return false;
    return raw === 'true';
  } catch {
    return false;
  }
}

export function setLiteUiEnabled(enabled) {
  try {
    localStorage.setItem(LITE_UI_KEY, enabled ? 'true' : 'false');
  } catch {
    /* ignore */
  }
}

export { LITE_UI_KEY };
