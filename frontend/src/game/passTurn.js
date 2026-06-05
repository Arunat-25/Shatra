import { COLOR_BLACK, COLOR_WHITE } from '../constants';

export function opponentColor(color) {
  if (color === COLOR_WHITE) return COLOR_BLACK;
  if (color === COLOR_BLACK) return COLOR_WHITE;
  return null;
}

/** Кнопка «Передать ход» только у игрока, который может передать ход бием. */
export function canShowPassTurn({ canPass, myColor, moversColor, posForMandatoryCapture }) {
  if (!canPass || !myColor || !moversColor) return false;
  if (posForMandatoryCapture != null) {
    return moversColor === myColor;
  }
  return moversColor !== myColor;
}

/** Цвет фигуры, которая может передать ход (после взятия бием). */
export function passTurnColor({ moversColor, posForMandatoryCapture }) {
  if (!moversColor) return null;
  if (posForMandatoryCapture != null) return moversColor;
  return opponentColor(moversColor);
}
