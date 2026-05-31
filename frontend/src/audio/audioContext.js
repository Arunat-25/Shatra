let ctx = null;

export function getAudioContext() {
  if (typeof window === 'undefined') return null;
  if (!ctx) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    ctx = new Ctx();
  }
  return ctx;
}

export async function resumeAudioContext() {
  const audio = getAudioContext();
  if (audio?.state === 'suspended') {
    await audio.resume();
  }
}
