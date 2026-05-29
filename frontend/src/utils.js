import { COLOR_WHITE, COLOR_BLACK, COLOR_WHITE_INCL, PIECE_BIY, PIECE_BATYR } from './constants';

import i18n from './i18n';
import { translateServerMessage } from './i18n/translateServerMessage';

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
/** Верх/низ доски в UI: сверху крепость соперника, снизу своя. */
export function getBoardSideOrder(myColor) {
  if (myColor === COLOR_BLACK) {
    return { top: COLOR_WHITE, bottom: COLOR_BLACK };
  }
  if (myColor === COLOR_WHITE) {
    return { top: COLOR_BLACK, bottom: COLOR_WHITE };
  }
  return { top: COLOR_WHITE, bottom: COLOR_BLACK };
}

export function colorToCountsKey(color) {
  return color === COLOR_WHITE ? 'white' : 'black';
}

export function readTimerSeconds(timer, color) {
  if (!timer) return null;
  if (timer[color] != null) return timer[color];
  return timer[colorToCountsKey(color)];
}

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

/** Убирает префикс «Игра окончена» из текста с сервера. */
export function stripGameOverLabel(text) {
  if (!text) return '';
  return String(text).replace(/^Игра окончена!?\s*:?\s*/i, '').trim();
}

/**
 * Текст окончания игры для UI.
 * @param {string} [winner]
 * @param {string} [reason] — timeout | resign | draw_agreed | opponent_disconnected
 */
export function formatGameOverMessage(winner, reason) {
  const t = i18n.t.bind(i18n);
  const cleanedWinner = stripGameOverLabel(winner);
  const translatedWinner = translateServerMessage(cleanedWinner || winner);
  const color = winnerColor(cleanedWinner || winner);

  if (reason === 'timeout') {
    if (color === 'белый') return t('result.timeoutWhite');
    if (color === 'чёрный') return t('result.timeoutBlack');
  }
  if (reason === 'resign') {
    if (color === 'белый') return t('result.resignWhite');
    if (color === 'чёрный') return t('result.resignBlack');
  }
  if (reason === 'draw_agreed') return t('result.drawAgreed');
  if (reason === 'cancelled') {
    return translatedWinner || t('result.cancelledDefault');
  }
  if (reason === 'opponent_disconnected') {
    if (color === 'белый') return t('result.disconnectWhite');
    if (color === 'чёрный') return t('result.disconnectBlack');
  }

  if (!cleanedWinner && !winner) return t('result.draw');

  if (translatedWinner && translatedWinner !== (cleanedWinner || winner)) {
    return translatedWinner;
  }

  if (cleanedWinner) return translateServerMessage(cleanedWinner);

  if (color) return t('result.biyWins', { color: t(`colors.${color === 'белый' ? 'white' : 'black'}`) });

  return translateServerMessage(winner) || t('result.draw');
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
  if (s >= 60 && s % 60 === 0) return i18n.t('time.minShort', { n: s / 60 });
  return i18n.t('time.secShort', { n: s });
}

/** Подпись контроля времени для зала ожидания: «15с + 1с», «1м + 15с», «∞» (без таймера) */
export function formatTimeControlLabel(timeControl, increment = 0) {
  if (timeControl == null) return i18n.t('time.unlimited');
  const base = formatDurationShort(timeControl);
  const inc = increment || 0;
  if (inc > 0) return `${base} + ${i18n.t('time.secShort', { n: inc })}`;
  return base;
}