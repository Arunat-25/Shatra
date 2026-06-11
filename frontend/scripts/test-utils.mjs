/**
 * Smoke-тесты formatGameOverMessage / formatClockTime (node, без импорта Vite-модулей).
 * Запуск: node frontend/scripts/test-utils.mjs
 */

function winnerColor(winner) {
  if (!winner) return null;
  const w = winner.toLowerCase();
  if (w.includes('бел')) return 'белый';
  if (w.includes('чер') || w.includes('чёр')) return 'чёрный';
  return null;
}

function stripGameOverLabel(text) {
  if (!text) return '';
  return String(text).replace(/^Игра окончена!?\s*:?\s*/i, '').trim();
}

function formatGameOverMessage(winner, reason) {
  const cleanedWinner = stripGameOverLabel(winner);
  const color = winnerColor(cleanedWinner || winner);
  const colorLabel = color === 'белый' ? 'белых' : color === 'чёрный' ? 'чёрных' : null;

  if (reason === 'timeout' && colorLabel) {
    const timedOutLabel = color === 'белый' ? 'чёрных' : 'белых';
    return `Время вышло у ${timedOutLabel}`;
  }
  if (reason === 'resign' && color) {
    const winnerLabel = color === 'белый' ? 'белые' : 'чёрные';
    return `${winnerLabel} победили (сдача)`;
  }
  if (reason === 'draw_agreed') {
    return 'Ничья по согласию';
  }
  if (reason === 'cancelled') {
    return winner || 'Игра отменена.';
  }
  if (reason === 'opponent_disconnected' && color) {
    const winnerLabel = color === 'белый' ? 'белые' : 'чёрные';
    return `${winnerLabel} победили (соперник отключился)`;
  }
  if (!cleanedWinner && !winner) return 'Ничья';
  if (cleanedWinner) return cleanedWinner;
  if (color) return `Победил ${color} Бий!`;
  return stripGameOverLabel(winner) || 'Ничья';
}

function formatClockTime(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return '—';
  const total = Math.max(0, Math.ceil(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function assert(cond, msg) {
  if (!cond) {
    console.error('FAIL:', msg);
    process.exit(1);
  }
}

assert(formatGameOverMessage('белый', 'timeout').includes('чёрных'), 'timeout: white won => black ran out');
assert(formatGameOverMessage('черный', 'timeout').includes('белых'), 'timeout: black won => white ran out');
assert(formatGameOverMessage('черный', 'resign').includes('сдача'), 'resign');
assert(formatGameOverMessage('x', 'draw_agreed').includes('согласию'), 'draw');
assert(formatGameOverMessage('Соперник отменил игру.', 'cancelled').includes('отменил'), 'cancelled');
assert(formatGameOverMessage('белый', 'opponent_disconnected').includes('отключился'), 'disconnect');
assert(formatGameOverMessage('Белый бий победил!').includes('победил'), 'biy');
assert(!formatGameOverMessage('белый', 'timeout').includes('Игра окончена'), 'no game-over label');
assert(
  formatGameOverMessage('Игра окончена: Белый бий победил!').includes('победил'),
  'strip server prefix',
);
assert(formatClockTime(65) === '1:05', 'clock 65');
assert(formatClockTime(15) === '0:15', 'clock 15');

console.log('OK: utils smoke tests passed');
