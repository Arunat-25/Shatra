export function isOwnColor(pieceName, color) {
  if (!pieceName) return false;
  if (pieceName.includes('бел')) return color.startsWith('бел');
  return color.startsWith('чер');
}

export function parsePieceName(name) {
  if (!name) throw new Error('Empty piece name');
  const color = name.includes('бел') ? 'белый' : 'черный';
  let pieceType = 'батыр';
  if (name.includes('шатра')) pieceType = 'шатра';
  else if (name.includes('бий')) pieceType = 'бий';
  return { color, pieceType };
}
