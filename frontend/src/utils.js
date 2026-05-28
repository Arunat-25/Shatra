import { COLOR_WHITE, COLOR_BLACK, COLOR_WHITE_INCL, PIECE_BIY, PIECE_BATYR } from './constants';

export { buildHintPayload, buildMovePayload, buildPassPayload, positionLabel } from './utils/wsPayloads';

/**
 * Преобразует ключи доски сервера (строки) в числа.
 */
export function convertKeys(serverBoard) {
  const result = {};
  for (const [key, value] of Object.entries(serverBoard)) {
    result[parseInt(key)] = value;
  }
  return result;
}

/**
 * Подсчитывает количество белых и чёрных фигур на доске.
 */
export function countPieces(boardData) {
  const pieces = Object.values(boardData);
  return {
    white: pieces.filter(v => v && v.includes(COLOR_WHITE_INCL)).length,
    black: pieces.filter(v => v && !v.includes(COLOR_WHITE_INCL)).length,
  };
}

/**
 * Подсчёт фигур по типам для белых/чёрных.
 * Возвращает количество только для батыр/шатра/бий.
 */
export function countPiecesByType(boardData) {
  const acc = {
    white: { batyr: 0, shatra: 0, biy: 0 },
    black: { batyr: 0, shatra: 0, biy: 0 },
  };
  for (const piece of Object.values(boardData)) {
    if (!piece) continue;
    const colorKey = piece.includes(COLOR_WHITE_INCL) ? 'white' : 'black';
    const type = getPieceType(piece);
    if (type === PIECE_BATYR) acc[colorKey].batyr += 1;
    else if (type === PIECE_BIY) acc[colorKey].biy += 1;
    else acc[colorKey].shatra += 1;
  }
  return acc;
}

/**
 * Определяет тип фигуры по строке с сервера.
 */
export function getPieceType(pieceStr) {
  if (pieceStr.includes(PIECE_BIY)) return PIECE_BIY;
  if (pieceStr.includes(PIECE_BATYR)) return PIECE_BATYR;
  return 'шатра';
}

/**
 * Определяет цвет фигуры по строке с сервера.
 */
export function getPieceColor(pieceStr) {
  return pieceStr.includes(COLOR_WHITE_INCL) ? COLOR_WHITE : COLOR_BLACK;
}

/**
 * Извлекает цвет победителя из строки winner (белый/чёрный).
 */
export function winnerColor(winner) {
  if (!winner) return null;
  const w = winner.toLowerCase();
  if (w.includes('бел')) return 'белый';
  if (w.includes('чер') || w.includes('чёр')) return 'чёрный';
  return null;
}

/**
 * Текст окончания игры для UI (две строки).
 * @param {string} [winner]
 * @param {string} [reason] — timeout | resign | draw_agreed | opponent_disconnected
 */
export function formatGameOverMessage(winner, reason) {
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

/** Формат mm:ss для игровых часов */
export function formatClockTime(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return '—';
  const total = Math.max(0, Math.ceil(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

/**
 * Определяет, является ли победитель текущим игроком.
 */
export function isWinner(winner, myColor) {
  const wColor = winnerColor(winner);
  if (!wColor || !myColor) return false;
  const mine = myColor.toLowerCase();
  return (mine.includes('бел') && wColor === 'белый') || (mine.includes('чер') && wColor === 'чёрный');
}

/** Краткая подпись длительности: 15с, 1м, 3м */
export function formatDurationShort(seconds) {
  const s = Math.round(seconds);
  if (s >= 60 && s % 60 === 0) return `${s / 60}м`;
  return `${s}с`;
}

/** Подпись контроля времени для зала ожидания: «15с + 1с», «1м + 15с», «без таймера» */
export function formatTimeControlLabel(timeControl, increment = 0) {
  if (timeControl == null) return 'без таймера';
  const base = formatDurationShort(timeControl);
  const inc = increment || 0;
  if (inc > 0) return `${base} + ${inc}с`;
  return base;
}