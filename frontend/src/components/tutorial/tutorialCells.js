/** Black fortress (крепость чёрных), cells 1–9. */
export const BLACK_FORTRESS_CELL_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9];

/** Black gate (ворота крепости чёрных), cell 10. */
export const BLACK_GATE_CELL_IDS = [10];

/** Main field (большое поле), cells 11–52. */
export const MAIN_FIELD_CELL_IDS = Array.from({ length: 42 }, (_, i) => 11 + i);

/** White gate (ворота крепости белых), cell 53. */
export const WHITE_GATE_CELL_IDS = [53];

/** White fortress (крепость белых), cells 54–62. */
export const WHITE_FORTRESS_CELL_IDS = [54, 55, 56, 57, 58, 59, 60, 61, 62];

/** Клетки превращения в батыра (game_engine PROMOTION_FOR_*). */
export const WHITE_SHATRA_BATYR_CELLS = [1, 2, 3];
export const BLACK_SHATRA_BATYR_CELLS = [60, 61, 62];

/** Ходы шатры по game_engine (get_hints) для урока раздела 2. */
export const WHITE_SHATRA_MOVE_TARGETS = {
  5: [1, 2, 3, 4, 6],
  4: [1, 2, 5],
  6: [2, 3, 5],
};
export const BLACK_SHATRA_MOVE_TARGETS = {
  58: [57, 59, 60, 61, 62],
  57: [58, 60, 61],
  59: [58, 61, 62],
};

export function getShatraMoveTargets(piece, fromCell) {
  const table = piece.includes('бел') ? WHITE_SHATRA_MOVE_TARGETS : BLACK_SHATRA_MOVE_TARGETS;
  return table[fromCell] ?? [];
}

export function findBoardCellWithPiece(board, piece) {
  for (let id = 1; id <= 62; id += 1) {
    if (board[id] === piece) return id;
  }
  return null;
}


export function allCellIdsExcept(keepIds) {
  const keep = new Set(keepIds);
  const out = [];
  for (let id = 1; id <= 62; id += 1) {
    if (!keep.has(id)) out.push(id);
  }
  return out;
}
