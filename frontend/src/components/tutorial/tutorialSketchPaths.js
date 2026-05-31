/** Hand-drawn style paths for tutorial zone highlights. */

function hash(i, salt = 0) {
  const n = Math.sin((i + salt) * 12.9898) * 43758.5453;
  return n - Math.floor(n);
}

function jitter(i, amount, salt = 0) {
  return (hash(i, salt) - 0.5) * 2 * amount;
}

export const SKETCH_OUTLINE_PADDING = 14;

/** Shared hand-drawn outline style for tutorial zone highlights. */
export const SKETCH_OUTLINE_STYLE = {
  wobble: 2.8,
  curve: 1.15,
  steps: 20,
};

/** Softer hand-drawn rings around spotlighted pieces (slide 4). */
export const SKETCH_PIECE_OUTLINE_STYLE = {
  wobble: 1.7,
  curve: 0.8,
  steps: 22,
};

export function expandRect(rect, padding = SKETCH_OUTLINE_PADDING) {
  return {
    left: rect.left - padding,
    top: rect.top - padding,
    width: rect.width + padding * 2,
    height: rect.height + padding * 2,
  };
}

/** Asymmetric padding — widen top/bottom edges without growing height as much. */
export function expandRectAxes(rect, padX, padY) {
  return {
    left: rect.left - padX,
    top: rect.top - padY,
    width: rect.width + padX * 2,
    height: rect.height + padY * 2,
  };
}

/** Closed wobbly loop around a rectangle (coords relative to overlay). */
export function sketchRectPath(
  rect,
  { padding = 0, wobble = 1.6, curve = 0.5, steps = 14, seed = 0 } = {},
) {
  const x = rect.left - padding;
  const y = rect.top - padding;
  const w = rect.width + padding * 2;
  const h = rect.height + padding * 2;
  const pts = [];

  for (let i = 0; i < steps; i += 1) {
    const t = i / steps;
    let px;
    let py;
    if (t < 0.25) {
      const u = t / 0.25;
      px = x + u * w;
      py = y;
    } else if (t < 0.5) {
      const u = (t - 0.25) / 0.25;
      px = x + w;
      py = y + u * h;
    } else if (t < 0.75) {
      const u = (t - 0.5) / 0.25;
      px = x + w - u * w;
      py = y + h;
    } else {
      const u = (t - 0.75) / 0.25;
      px = x;
      py = y + h - u * h;
    }
    pts.push([
      px + jitter(i, wobble, seed),
      py + jitter(i + 7, wobble, seed + 1),
    ]);
  }

  const [fx, fy] = pts[0];
  let d = `M ${fx.toFixed(1)} ${fy.toFixed(1)}`;
  for (let i = 1; i < pts.length; i += 1) {
    const [cx, cy] = pts[i];
    const [px, py] = pts[i - 1];
    const mx = (px + cx) / 2 + jitter(i + 20, wobble * curve, seed);
    const my = (py + cy) / 2 + jitter(i + 21, wobble * curve, seed + 1);
    d += ` Q ${mx.toFixed(1)} ${my.toFixed(1)} ${cx.toFixed(1)} ${cy.toFixed(1)}`;
  }
  d += ' Z';
  return d;
}

/** Closed wobbly circle/ellipse from a bounding rect (hand-drawn ring). */
export function sketchCirclePath(
  rect,
  { wobble = 1.6, curve = 0.5, steps = 18, seed = 0 } = {},
) {
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  const rx = rect.width / 2;
  const ry = rect.height / 2;
  const pts = [];

  for (let i = 0; i < steps; i += 1) {
    const angle = (i / steps) * Math.PI * 2;
    pts.push([
      cx + Math.cos(angle) * rx + jitter(i, wobble, seed),
      cy + Math.sin(angle) * ry + jitter(i + 7, wobble, seed + 1),
    ]);
  }

  const [fx, fy] = pts[0];
  let d = `M ${fx.toFixed(1)} ${fy.toFixed(1)}`;
  for (let i = 1; i < pts.length; i += 1) {
    const [px, py] = pts[i];
    const [prevX, prevY] = pts[i - 1];
    const mx = (prevX + px) / 2 + jitter(i + 20, wobble * curve, seed);
    const my = (prevY + py) / 2 + jitter(i + 21, wobble * curve, seed + 1);
    d += ` Q ${mx.toFixed(1)} ${my.toFixed(1)} ${px.toFixed(1)} ${py.toFixed(1)}`;
  }
  d += ' Z';
  return d;
}

/** Shorten arrow along its axis from start and/or end. */
export function trimArrowEnds(fromX, fromY, toX, toY, startTrimPx, endTrimPx) {
  const dx = toX - fromX;
  const dy = toY - fromY;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  return {
    fromX: fromX + ux * startTrimPx,
    fromY: fromY + uy * startTrimPx,
    toX: toX - ux * endTrimPx,
    toY: toY - uy * endTrimPx,
  };
}

/** 0 = almost straight, 1 = full sketch curve (~50px → ~140px). */
function arrowCurveFactor(len) {
  return Math.min(1, Math.max(0, (len - 50) / 90));
}

/** Sketchy arrow from board zone toward label anchor — wobbly multi-segment curve. */
export function sketchArrowPath(fromX, fromY, toX, toY, seed = 0, options = {}) {
  const { curveBoost = 0 } = options;
  const dx = toX - fromX;
  const dy = toY - fromY;
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const nx = -uy;
  const ny = ux;

  const curveT = Math.max(0, Math.min(1, arrowCurveFactor(len) + curveBoost));
  const bowMax = Math.min(len * 0.16, 18) * curveT * (1 + Math.max(0, curveBoost) * 0.35);
  const segJ = 4 * curveT;
  const ctrlJ = 6 * curveT;
  const multiCutoff = 0.5 - Math.min(Math.max(0, curveBoost), 0.45);

  let d;
  let angle;

  if (curveT < multiCutoff) {
    const mx = (fromX + toX) / 2 + nx * bowMax * 0.65 + jitter(1, Math.max(1.5, segJ), seed);
    const my = (fromY + toY) / 2 + ny * bowMax * 0.65 + jitter(2, Math.max(1.5, segJ), seed + 2);
    d = `M ${fromX.toFixed(1)} ${fromY.toFixed(1)} Q ${mx.toFixed(1)} ${my.toFixed(1)} ${toX.toFixed(1)} ${toY.toFixed(1)}`;
    angle = Math.atan2(toY - my, toX - mx);
  } else {
    const bow1 = jitter(1, bowMax, seed);
    const bow2 = jitter(2, bowMax * 0.55, seed + 4);

    const x1 = fromX + ux * len * 0.38 + nx * bow1 + jitter(5, segJ, seed + 1);
    const y1 = fromY + uy * len * 0.38 + ny * bow1 + jitter(6, segJ, seed + 2);
    const x2 = fromX + ux * len * 0.72 + nx * bow2 + jitter(7, segJ, seed + 3);
    const y2 = fromY + uy * len * 0.72 + ny * bow2 + jitter(8, segJ, seed + 5);

    const c1x = fromX + (x1 - fromX) * 0.52 + jitter(10, ctrlJ, seed);
    const c1y = fromY + (y1 - fromY) * 0.52 + jitter(11, ctrlJ, seed + 6);
    const c2x = x1 + (x2 - x1) * 0.48 + jitter(12, ctrlJ, seed + 7);
    const c2y = y1 + (y2 - y1) * 0.48 + jitter(13, ctrlJ, seed + 8);
    const c3x = x2 + (toX - x2) * 0.52 + jitter(14, ctrlJ * 0.85, seed + 9);
    const c3y = y2 + (toY - y2) * 0.52 + jitter(15, ctrlJ * 0.85, seed + 10);

    d = `M ${fromX.toFixed(1)} ${fromY.toFixed(1)}`;
    d += ` Q ${c1x.toFixed(1)} ${c1y.toFixed(1)} ${x1.toFixed(1)} ${y1.toFixed(1)}`;
    d += ` Q ${c2x.toFixed(1)} ${c2y.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`;
    d += ` Q ${c3x.toFixed(1)} ${c3y.toFixed(1)} ${toX.toFixed(1)} ${toY.toFixed(1)}`;
    angle = Math.atan2(toY - c3y, toX - c3x);
  }
  const head = 7;
  const a1 = angle + Math.PI * 0.82;
  const a2 = angle - Math.PI * 0.82;
  const hx1 = toX + Math.cos(a1) * head;
  const hy1 = toY + Math.sin(a1) * head;
  const hx2 = toX + Math.cos(a2) * head;
  const hy2 = toY + Math.sin(a2) * head;

  return {
    shaft: d,
    head: `M ${toX.toFixed(1)} ${toY.toFixed(1)} L ${hx1.toFixed(1)} ${hy1.toFixed(1)} M ${toX.toFixed(1)} ${toY.toFixed(1)} L ${hx2.toFixed(1)} ${hy2.toFixed(1)}`,
  };
}

export function measureCssLengthPx(wrapEl, length) {
  const probe = document.createElement('div');
  probe.style.cssText = 'position:absolute;visibility:hidden;pointer-events:none';
  probe.style.width = length;
  wrapEl.appendChild(probe);
  const px = probe.getBoundingClientRect().width;
  probe.remove();
  return px;
}

/** Shift top rects up and bottom rects down (relative coords). */
export function offsetRectsVerticalByHalf(
  rects,
  boardRect,
  wrapEl,
  { topMm = 8, bottomMm = 8 } = {},
) {
  if (!rects.length || !boardRect) return rects;
  const topDy = measureCssLengthPx(wrapEl, `${topMm}mm`);
  const bottomDy = measureCssLengthPx(wrapEl, `${bottomMm}mm`);
  const boardMid = boardRect.top + boardRect.height / 2;
  return rects.map((r) => {
    const cy = r.top + r.height / 2;
    return {
      ...r,
      top: cy < boardMid ? r.top - topDy : r.top + bottomDy,
    };
  });
}

/** @deprecated Use offsetRectsVerticalByHalf */
export const offsetGateRectsVertical = offsetRectsVerticalByHalf;

/** Asymmetric 1 mm stretch for fortress tutorial outlines (slide 2). */
export function expandFortressOutlineRect(rect, wrapEl, position) {
  const mm = measureCssLengthPx(wrapEl, '1mm');
  if (position === 'upper') {
    return {
      left: rect.left - mm,
      top: rect.top - mm,
      width: rect.width + mm,
      height: rect.height + mm,
    };
  }
  return {
    left: rect.left,
    top: rect.top,
    width: rect.width + mm,
    height: rect.height + mm,
  };
}

/** Extend side edges: upper outline upward, lower outline downward. */
export function extendFortressSidesVertical(rect, wrapEl, position) {
  const mm = measureCssLengthPx(wrapEl, '2mm');
  if (position === 'upper') {
    return { ...rect, top: rect.top - mm, height: rect.height + mm };
  }
  return { ...rect, height: rect.height + mm };
}

export function mergeRelativeRects(rects) {
  if (!rects.length) return null;
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const r of rects) {
    minX = Math.min(minX, r.left);
    minY = Math.min(minY, r.top);
    maxX = Math.max(maxX, r.left + r.width);
    maxY = Math.max(maxY, r.top + r.height);
  }
  return {
    left: minX,
    top: minY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

export function measureZoneRects(wrapEl, selector) {
  const wrapRect = wrapEl.getBoundingClientRect();
  const nodes = wrapEl.querySelectorAll(selector);
  return Array.from(nodes).map((node) => {
    const r = node.getBoundingClientRect();
    return {
      left: r.left - wrapRect.left,
      top: r.top - wrapRect.top,
      width: r.width,
      height: r.height,
    };
  });
}

export function anchorOnRectEdge(rect, side = 'right') {
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  if (side === 'right') {
    return { x: rect.left + rect.width, y: cy };
  }
  if (side === 'left') {
    return { x: rect.left, y: cy };
  }
  return { x: cx, y: rect.top + rect.height };
}

/** Closest point on rect (including edges) to an external point. */
export function nearestPointOnRect(rect, px, py) {
  return {
    x: Math.max(rect.left, Math.min(px, rect.left + rect.width)),
    y: Math.max(rect.top, Math.min(py, rect.top + rect.height)),
  };
}

/** Point on rect border in the direction of a target. */
export function anchorOnRectBorderToward(rect, tx, ty) {
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  const dx = tx - cx;
  const dy = ty - cy;
  if (Math.abs(dx) < 1e-6 && Math.abs(dy) < 1e-6) {
    return { x: cx, y: cy };
  }
  const halfW = rect.width / 2;
  const halfH = rect.height / 2;
  const scale = 1 / Math.max(Math.abs(dx) / halfW, Math.abs(dy) / halfH);
  return { x: cx + dx * scale, y: cy + dy * scale };
}

export function anchorOnRectCorner(rect, corner = 'bottom-left') {
  if (corner === 'bottom-right') {
    return { x: rect.left + rect.width, y: rect.top + rect.height };
  }
  if (corner === 'top-left') {
    return { x: rect.left, y: rect.top };
  }
  if (corner === 'top-right') {
    return { x: rect.left + rect.width, y: rect.top };
  }
  return { x: rect.left, y: rect.top + rect.height };
}

export function measureRelativeRect(wrapEl, selector) {
  const wrapRect = wrapEl.getBoundingClientRect();
  const node = wrapEl.querySelector(selector);
  if (!node) return null;
  const r = node.getBoundingClientRect();
  return {
    left: r.left - wrapRect.left,
    top: r.top - wrapRect.top,
    width: r.width,
    height: r.height,
    right: r.right - wrapRect.left,
    bottom: r.bottom - wrapRect.top,
  };
}

/** Place label on panel background beside the board (not over the board). */
export function placeLabelBesideBoard(boardRect, wrapSize, anchorY, labelText) {
  const gap = 12;
  const margin = 8;
  const estWidth = Math.min(120, labelText.length * 7.5 + 20);
  const estHeight = 28;

  let left = boardRect.right + gap;
  let top = anchorY;

  if (left + estWidth > wrapSize.width - margin) {
    left = Math.max(margin, boardRect.left);
    top = boardRect.bottom + gap;
    return {
      left,
      top,
      transform: 'none',
      placement: 'below',
      anchorX: left,
      anchorY: top + estHeight / 2,
      textAlign: 'left',
    };
  }

  if (top - estHeight / 2 < margin) top = margin + estHeight / 2;
  if (top + estHeight / 2 > wrapSize.height - margin) {
    top = wrapSize.height - margin - estHeight / 2;
  }

  return {
    left,
    top,
    transform: 'translateY(-50%)',
    placement: 'beside',
    anchorX: left,
    anchorY: top,
    textAlign: 'left',
  };
}
