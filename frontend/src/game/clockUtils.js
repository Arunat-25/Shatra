/** Smooth local countdown between server clock syncs (Lichess-style). */
export function computeDisplayTimer({
  timer,
  timerSyncedAt,
  moversColor,
  timeControl,
  gameOver,
  waiting,
}) {
  if (!timeControl || !timer || gameOver || waiting) {
    return timer;
  }
  if (timerSyncedAt == null) {
    return timer;
  }

  const elapsedSec = (Date.now() - timerSyncedAt) / 1000;
  const next = { ...timer };
  if (moversColor === 'белый' && next.белый != null) {
    next.белый = Math.max(0, Number(next.белый) - elapsedSec);
  } else if (moversColor === 'черный' && next.черный != null) {
    next.черный = Math.max(0, Number(next.черный) - elapsedSec);
  }
  return next;
}
