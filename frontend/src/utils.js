import { COLOR_WHITE, COLOR_WHITE_INCL, PIECE_BIY, PIECE_BATYR } from './constants';

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
  return pieceStr.includes(COLOR_WHITE_INCL) ? COLOR_WHITE : 'черный';
}

/**
 * Определяет, является ли победитель текущим игроком.
 */
export function isWinner(winner, myColor) {
  if (!winner) return false;
  const winnerIncl = winner.includes(COLOR_WHITE_INCL) ? COLOR_WHITE_INCL : 'чер';
  return myColor.includes(winnerIncl);
}

const CLIENT_ID_KEY = 'shatra_client_id';

/**
 * Возвращает UUID анонимного игрока. Создаётся один раз, хранится в localStorage.
 */
export function getClientId() {
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
}

/**
 * Формирует WebSocket URL.
 */
export function getWsUrl(roomId, playerId) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/${roomId}/?player=${playerId || ''}&client_id=${getClientId()}`;
}
