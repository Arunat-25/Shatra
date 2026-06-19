/**
 * Pick drop cell from pointer: full cell bounds first, then snap to nearest legal dest.
 */
export function resolveSnapDrop({
  clientX,
  clientY,
  from,
  legalDests,
  resolveCellAt,
  getCellCenter,
}) {
  const destList = legalDests instanceof Set
    ? [...legalDests]
    : Array.isArray(legalDests)
      ? legalDests
      : [];

  if (!destList.length) {
    const direct = resolveCellAt?.(clientX, clientY);
    return direct != null && direct !== from ? direct : null;
  }

  if (!getCellCenter) {
    const direct = resolveCellAt?.(clientX, clientY);
    return direct != null && direct !== from ? direct : null;
  }

  const referenceSize = getCellCenter(from)?.size
    ?? destList.map((id) => getCellCenter(id)?.size).find((s) => s != null)
    ?? 48;
  const snapRadius = referenceSize * 1.05;

  for (const cellId of destList) {
    if (cellId === from) continue;
    const center = getCellCenter(cellId);
    if (!center) continue;
    const half = (center.size ?? referenceSize) / 2;
    if (
      Math.abs(clientX - center.x) <= half
      && Math.abs(clientY - center.y) <= half
    ) {
      return cellId;
    }
  }

  const direct = resolveCellAt?.(clientX, clientY);
  if (direct != null && direct !== from && destList.includes(direct)) {
    return direct;
  }

  let best = null;
  let bestDist = Infinity;
  for (const cellId of destList) {
    if (cellId === from) continue;
    const center = getCellCenter(cellId);
    if (!center) continue;
    const dist = Math.hypot(clientX - center.x, clientY - center.y);
    if (dist <= snapRadius && dist < bestDist) {
      bestDist = dist;
      best = cellId;
    }
  }
  return best;
}
