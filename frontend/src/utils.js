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
 * Определяет, является ли победитель текущим игроком.
 */
export function isWinner(winner, myColor) {
  return !!(winner && winner === myColor);
}