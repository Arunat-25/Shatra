import { COLOR_WHITE, COLOR_BLACK, COLOR_WHITE_INCL, PIECE_BIY, PIECE_BATYR } from './constants';

import i18n from './i18n';
import { resolveMessageCode } from './i18n/resolveMessage';

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

/** Нормализует winner_color / legacy winner text to «белый» | «чёрный». */
export function winnerColor(raw) {
  if (!raw) return null;
  const w = String(raw).toLowerCase();
  if (w.includes('бел') || w === 'white') return COLOR_WHITE;
  if (w.includes('чер') || w.includes('чёр') || w === 'black') return COLOR_BLACK;
  return null;
}

/**
 * Текст окончания игры для UI.
 * @param {string} [winnerColor] — «белый» / «черный»
 * @param {string} [reason] — timeout | resign | draw_agreed | draw_two_biys | draw_repetition | cancelled | opponent_disconnected
 * @param {string} [messageCode] — cancel.* codes when reason is cancelled
 */
export function formatGameOverMessage(winnerColorRaw, reason, messageCode) {
  const t = i18n.t.bind(i18n);
  const color = winnerColor(winnerColorRaw);

  if (reason === 'draw_two_biys' || reason === 'draw_repetition') {
    return resolveMessageCode(reason) || t('result.drawAgreed');
  }
  if (reason === 'draw_agreed') return t('result.drawAgreed');

  if (reason === 'timeout') {
    // winner_color is who won; timeout message names who ran out of time (the loser).
    if (color === COLOR_WHITE) return t('result.timeoutBlack');
    if (color === COLOR_BLACK) return t('result.timeoutWhite');
  }
  if (reason === 'resign') {
    if (color === COLOR_WHITE) return t('result.resignWhite');
    if (color === COLOR_BLACK) return t('result.resignBlack');
  }
  if (reason === 'cancelled') {
    return messageCode
      ? resolveMessageCode(messageCode)
      : t('result.cancelledDefault');
  }
  if (reason === 'opponent_disconnected') {
    if (color === COLOR_WHITE) return t('result.disconnectWhite');
    if (color === COLOR_BLACK) return t('result.disconnectBlack');
  }

  if (!color && !winnerColorRaw) return t('result.draw');

  if (color) {
    return t('result.biyWins', {
      color: t(`colors.${color === COLOR_WHITE ? 'white' : 'black'}`),
    });
  }

  return t('result.draw');
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
export function isWinner(winnerColorRaw, myColor) {
  const wColor = winnerColor(winnerColorRaw);
  if (!wColor || !myColor) return false;
  const mine = myColor.toLowerCase();
  return (mine.includes('бел') && wColor === COLOR_WHITE)
    || (mine.includes('чер') && wColor === COLOR_BLACK);
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
