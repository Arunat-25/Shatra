/**
 * Apply a confirmed v2 move delta onto a board map (numeric cell keys).
 */
export function applyMoveDelta(board, { from, to, captured = [], promoted = false }) {
  const next = { ...board };
  const fromCell = Number(from);
  const toCell = Number(to);
  if (!fromCell || !toCell) return next;

  const piece = next[fromCell];
  if (piece == null) return next;

  for (const pos of captured || []) {
    const cell = Number(pos);
    if (cell) next[cell] = null;
  }

  next[toCell] = piece;
  next[fromCell] = null;

  if (promoted && piece.includes('шатра')) {
    next[toCell] = piece.includes('бел') ? 'белый батыр' : 'черный батыр';
  }

  return next;
}
