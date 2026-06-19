const EDGE_PADDING = 4;
const PIECE_SCALE = 0.92;

function toDestList(legalDests) {
  if (legalDests instanceof Set) return [...legalDests];
  if (Array.isArray(legalDests)) return legalDests;
  return [];
}

function cellBoundsFromCenter(center, referenceSize) {
  const half = (center.size ?? referenceSize) / 2;
  return {
    left: center.x - half,
    top: center.y - half,
    right: center.x + half,
    bottom: center.y + half,
  };
}

function resolveCellBounds(cellId, getCellBounds, getCellCenter, referenceSize) {
  const exact = getCellBounds?.(cellId);
  if (exact) return exact;
  const center = getCellCenter?.(cellId);
  if (!center) return null;
  return cellBoundsFromCenter(center, referenceSize);
}

function pieceBounds(x, y, size, referenceSize) {
  const half = ((size ?? referenceSize) * PIECE_SCALE * 1.08) / 2;
  return {
    left: x - half,
    top: y - half,
    right: x + half,
    bottom: y + half,
  };
}

function overlapArea(a, b) {
  const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
  const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
  if (w <= 0 || h <= 0) return 0;
  return w * h;
}

function pointInCellZone(x, y, bounds) {
  return (
    x >= bounds.left - EDGE_PADDING
    && x <= bounds.right + EDGE_PADDING
    && y >= bounds.top - EDGE_PADDING
    && y <= bounds.bottom + EDGE_PADDING
  );
}

function isAllowedTarget(cellId, from, destList) {
  if (cellId == null || cellId === from) return false;
  if (!destList.length) return true;
  return destList.includes(cellId);
}

function pickByPieceOverlap(destList, ghost, getCellBounds, getCellCenter, referenceSize) {
  if (!ghost || !destList.length) return null;
  const piece = pieceBounds(ghost.x, ghost.y, ghost.size, referenceSize);
  let bestId = null;
  let bestArea = 0;
  for (const cellId of destList) {
    const bounds = resolveCellBounds(cellId, getCellBounds, getCellCenter, referenceSize);
    if (!bounds) continue;
    const area = overlapArea(piece, bounds);
    if (area > bestArea) {
      bestArea = area;
      bestId = cellId;
    }
  }
  return bestArea > 0 ? bestId : null;
}

/**
 * Drop if cursor is in cell OR dragged piece overlaps cell (any overlap counts).
 */
export function resolveSnapDrop({
  clientX,
  clientY,
  from,
  legalDests,
  resolveCellAt,
  getCellCenter,
  getCellBounds,
  ghost,
}) {
  const destList = toDestList(legalDests).filter((id) => id !== from);
  const referenceSize = getCellCenter?.(from)?.size
    ?? destList.map((id) => getCellCenter?.(id)?.size).find((s) => s != null)
    ?? ghost?.size
    ?? 48;

  const byOverlap = pickByPieceOverlap(
    destList,
    ghost,
    getCellBounds,
    getCellCenter,
    referenceSize,
  );
  if (byOverlap != null) return byOverlap;

  const underCursor = resolveCellAt?.(clientX, clientY);
  if (isAllowedTarget(underCursor, from, destList)) {
    return underCursor;
  }

  const candidates = destList.length
    ? destList
    : (underCursor != null && underCursor !== from ? [underCursor] : []);

  for (const cellId of candidates) {
    const bounds = resolveCellBounds(cellId, getCellBounds, getCellCenter, referenceSize);
    if (bounds && pointInCellZone(clientX, clientY, bounds)) {
      return cellId;
    }
  }

  return null;
}
