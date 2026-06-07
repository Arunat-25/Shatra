import { COLOR_BLACK, COLOR_WHITE } from '../constants';

export function opponentColor(color) {
  if (color === COLOR_WHITE) return COLOR_BLACK;
  if (color === COLOR_BLACK) return COLOR_WHITE;
  return null;
}

/** Кнопка «Передать ход» только во время серии взятий бием (есть продолжение). */
export function canShowPassTurn({ canPass, myColor, moversColor, posForMandatoryCapture }) {
  if (!canPass || !myColor || !moversColor) return false;
  return posForMandatoryCapture != null && moversColor === myColor;
}

/** Цвет игрока, который может передать ход (бий в серии взятий). */
export function passTurnColor({ moversColor, posForMandatoryCapture }) {
  if (!moversColor || posForMandatoryCapture == null) return null;
  return moversColor;
}
