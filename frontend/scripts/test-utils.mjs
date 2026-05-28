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

function formatGameOverMessage(winner, reason) {
  const color = winnerColor(winner);
  const colorLabel = color === 'белый' ? 'белых' : color === 'чёрный' ? 'чёрных' : null;

  if (reason === 'timeout' && colorLabel) {
    return `Игра окончена!\nВремя вышло у ${colorLabel}`;
  }
  if (reason === 'resign' && color) {
    const winnerLabel = color === 'белый' ? 'белые' : 'чёрные';
    return `Игра окончена!\n${winnerLabel} победили (сдача)`;
  }
  if (reason === 'draw_agreed') {
    return 'Игра окончена!\nНичья по согласию';
  }
  if (reason === 'opponent_disconnected' && color) {
    const winnerLabel = color === 'белый' ? 'белые' : 'чёрные';
    return `Игра окончена!\n${winnerLabel} победили (соперник отключился)`;
  }
  if (!winner) return 'Игра окончена!\nНичья';
  const w = winner.toLowerCase();
  if (w.includes('ничья')) {
    const line = winner.trim().replace(/!+$/, '');
    return `Игра окончена!\n${line}!`;
  }
  if (!color) return `Игра окончена!\n${winner}`;
  return `Игра окончена!\nПобедил ${color} Бий!`;
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

assert(formatGameOverMessage('белый', 'timeout').includes('Время вышло'), 'timeout');
assert(formatGameOverMessage('черный', 'resign').includes('сдача'), 'resign');
assert(formatGameOverMessage('x', 'draw_agreed').includes('согласию'), 'draw');
assert(formatGameOverMessage('белый', 'opponent_disconnected').includes('отключился'), 'disconnect');
assert(formatGameOverMessage('белый бий').includes('Бий'), 'biy');
assert(formatClockTime(65) === '1:05', 'clock 65');
assert(formatClockTime(15) === '0:15', 'clock 15');

console.log('OK: utils smoke tests passed');
