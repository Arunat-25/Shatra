import { getBoardSections } from '../constants';

/** Total row-units (incl. reserve 0.86 rows); matches --board-unit in game.css. */
export const BOARD_HEIGHT_UNITS = 13.6;
/** Row-units with zero section margins (mobile compact). 2×3×0.86 + 2×1 + 6×1 */
export const BOARD_HEIGHT_UNITS_COMPACT = 13.16;
export const BOARD_WIDTH_CELLS = 7;

const DEFAULT_RESERVE_MARGIN = 3;
const DEFAULT_MAIN_MARGIN = 1;
const DEFAULT_KING_MARGIN = '1mm';
const DEFAULT_CELL_NUMBER_SCALE = 0.19;

/**
 * Mirrors `--cell-number-scale` on `.board` (board.css).
 * @param {HTMLElement | null | undefined} boardEl
 */
export function readCellNumberScale(boardEl) {
  if (!boardEl || typeof getComputedStyle === 'undefined') return DEFAULT_CELL_NUMBER_SCALE;
  const raw = getComputedStyle(boardEl).getPropertyValue('--cell-number-scale').trim();
  const scale = parseFloat(raw);
  return Number.isFinite(scale) && scale > 0 ? scale : DEFAULT_CELL_NUMBER_SCALE;
}

/**
 * Mirrors `--board-height-units` on `.board` (game.css / game-mobile.css).
 * @param {HTMLElement | null | undefined} boardEl
 */
export function readBoardHeightUnits(boardEl) {
  if (!boardEl || typeof getComputedStyle === 'undefined') return BOARD_HEIGHT_UNITS;
  const raw = getComputedStyle(boardEl).getPropertyValue('--board-height-units').trim();
  const units = parseFloat(raw);
  return Number.isFinite(units) && units > 0 ? units : BOARD_HEIGHT_UNITS;
}

function parseCssLengthToPx(value, refEl, fallbackPx) {
  if (!value?.trim() || !refEl) return fallbackPx;
  const probe = document.createElement('div');
  probe.style.position = 'absolute';
  probe.style.visibility = 'hidden';
  probe.style.pointerEvents = 'none';
  probe.style.height = value.trim();
  refEl.appendChild(probe);
  const px = probe.getBoundingClientRect().height;
  probe.remove();
  return px > 0 ? px : fallbackPx;
}

function sectionMarginPx(className, metrics) {
  if (className === 'field-of-reserve') return metrics.reserveMargin;
  if (className === 'field-of-king') return metrics.kingMargin;
  return metrics.mainMargin;
}

/**
 * Read cell metrics from `.board` CSS variables (same source as DOM `.kletka` sizing).
 * @param {HTMLElement | null | undefined} boardEl
 */
export function readBoardUnitMetrics(boardEl) {
  if (!boardEl || typeof getComputedStyle === 'undefined') return null;

  const cs = getComputedStyle(boardEl);
  let cellSize = parseFloat(cs.getPropertyValue('--cell-size'));
  let reserveSize = parseFloat(cs.getPropertyValue('--reserve-cell-size'));

  if (!Number.isFinite(cellSize) || cellSize <= 0) {
    const derived = deriveMetricsFromBoardSlot(boardEl);
    if (!derived) return null;
    cellSize = derived.cellSize;
    reserveSize = derived.reserveSize;
  }

  if (!Number.isFinite(reserveSize) || reserveSize <= 0) {
    reserveSize = cellSize * 0.86;
  }

  const kingMarginRaw = cs.getPropertyValue('--king-field-margin').trim() || DEFAULT_KING_MARGIN;
  const reserveMarginRaw = cs.getPropertyValue('--reserve-field-margin').trim();
  const mainMarginRaw = cs.getPropertyValue('--main-field-margin').trim();
  const heightUnits = readBoardHeightUnits(boardEl);

  return {
    cellSize,
    reserveSize,
    heightUnits,
    reserveMargin: reserveMarginRaw
      ? parseCssLengthToPx(reserveMarginRaw, boardEl, DEFAULT_RESERVE_MARGIN)
      : DEFAULT_RESERVE_MARGIN,
    mainMargin: mainMarginRaw
      ? parseCssLengthToPx(mainMarginRaw, boardEl, DEFAULT_MAIN_MARGIN)
      : DEFAULT_MAIN_MARGIN,
    kingMargin: parseCssLengthToPx(kingMarginRaw, boardEl, 3.78),
  };
}

/**
 * Fallback when custom properties are not resolved yet (mirrors game.css / game-mobile.css).
 */
export function deriveMetricsFromBoardSlot(boardEl) {
  const slot = boardEl?.closest?.('.room-board');
  if (!slot) return null;

  const cw = Math.max(0, slot.clientWidth);
  const ch = Math.max(0, slot.clientHeight);
  const innerW = Math.max(0, cw - 20);
  const innerH = Math.max(0, ch - 20);
  const heightUnits = readBoardHeightUnits(boardEl);
  const unit = ch >= 120
    ? Math.min(innerW / BOARD_WIDTH_CELLS, innerH / heightUnits)
    : innerW / BOARD_WIDTH_CELLS;

  if (!Number.isFinite(unit) || unit <= 0) return null;

  const cs = boardEl && typeof getComputedStyle !== 'undefined'
    ? getComputedStyle(boardEl)
    : null;
  const reserveMarginRaw = cs?.getPropertyValue('--reserve-field-margin').trim();
  const mainMarginRaw = cs?.getPropertyValue('--main-field-margin').trim();
  const kingMarginRaw = cs?.getPropertyValue('--king-field-margin').trim() || DEFAULT_KING_MARGIN;

  return {
    cellSize: unit,
    reserveSize: unit * 0.86,
    heightUnits,
    reserveMargin: reserveMarginRaw
      ? parseCssLengthToPx(reserveMarginRaw, boardEl, DEFAULT_RESERVE_MARGIN)
      : DEFAULT_RESERVE_MARGIN,
    mainMargin: mainMarginRaw
      ? parseCssLengthToPx(mainMarginRaw, boardEl, DEFAULT_MAIN_MARGIN)
      : DEFAULT_MAIN_MARGIN,
    kingMargin: parseCssLengthToPx(kingMarginRaw, boardEl, 3.78),
  };
}

/**
 * Lay out cells using the same unit sizes as the DOM board grid.
 * @param {string} myColor
 * @param {{ cellSize: number, reserveSize: number, reserveMargin?: number, mainMargin?: number, kingMargin?: number }} metrics
 */
export function computeBoardLayout(myColor, metrics) {
  const sections = getBoardSections(myColor);
  const cellSize = metrics.cellSize;
  const reserveSize = metrics.reserveSize;
  const reserveMargin = metrics.reserveMargin ?? DEFAULT_RESERVE_MARGIN;
  const mainMargin = metrics.mainMargin ?? DEFAULT_MAIN_MARGIN;
  const kingMargin = metrics.kingMargin ?? 3.78;
  const marginMetrics = { reserveMargin, mainMargin, kingMargin };

  const boardWidth = BOARD_WIDTH_CELLS * cellSize;
  const cells = {};
  let y = 0;
  const centerX = boardWidth / 2;
  let prevSectionClass = null;

  for (const section of sections) {
    const margin = sectionMarginPx(section.class, marginMetrics);
    if (prevSectionClass == null) {
      y += margin;
    } else {
      y += sectionMarginPx(prevSectionClass, marginMetrics) + margin;
    }
    prevSectionClass = section.class;

    const rowCellSize = section.class === 'field-of-reserve' ? reserveSize : cellSize;

    for (const row of section.rows) {
      const rowWidth = row.length * rowCellSize;
      let x = centerX - rowWidth / 2;
      for (const cell of row) {
        cells[cell.id] = {
          x,
          y,
          w: rowCellSize,
          h: rowCellSize,
          colorClass: cell.color,
          sectionClass: section.class,
        };
        x += rowCellSize;
      }
      y += rowCellSize;
    }
  }

  if (prevSectionClass) {
    y += sectionMarginPx(prevSectionClass, marginMetrics);
  }

  const contentHeight = y;
  const heightUnits = metrics.heightUnits ?? BOARD_HEIGHT_UNITS;
  const designHeight = heightUnits * cellSize;
  const height = Math.max(contentHeight, designHeight);

  return {
    cells,
    cellSize,
    reserveSize,
    width: boardWidth,
    height,
    contentHeight,
    boardWidth,
  };
}

/**
 * Map layout coordinates to display pixels when the canvas fills its slot.
 * Uniform scale keeps cells square (same idea as min(cqw/7, cqh/units) on DOM board).
 * @returns {{ x: number, y: number, offsetX: number, offsetY: number }}
 */
export function layoutDrawScale(layout, displayW, displayH, fillSlot) {
  if (!fillSlot) {
    return { x: 1, y: 1, offsetX: 0, offsetY: 0 };
  }
  if (!layout?.width || !layout?.contentHeight || displayW <= 0 || displayH <= 0) {
    return { x: 1, y: 1, offsetX: 0, offsetY: 0 };
  }
  const scale = Math.min(displayW / layout.width, displayH / layout.contentHeight);
  return {
    x: scale,
    y: scale,
    offsetX: (displayW - layout.width * scale) / 2,
    offsetY: (displayH - layout.contentHeight * scale) / 2,
  };
}

/**
 * Convert viewport (client) coordinates to canvas layout space used by drawBoard.
 * @param {number} clientX
 * @param {number} clientY
 * @param {{ left: number, top: number, width: number, height: number }} canvasRect
 */
export function viewportToLayoutPoint(clientX, clientY, canvasRect, layout, fillSlot) {
  const scale = layoutDrawScale(layout, canvasRect.width, canvasRect.height, fillSlot);
  return {
    x: (clientX - canvasRect.left - scale.offsetX) / scale.x,
    y: (clientY - canvasRect.top - scale.offsetY) / scale.y,
    scale,
  };
}

export function hitTestCell(cells, x, y, padding = 3) {
  for (const [id, rect] of Object.entries(cells)) {
    if (
      x >= rect.x - padding
      && x < rect.x + rect.w + padding
      && y >= rect.y - padding
      && y < rect.y + rect.h + padding
    ) {
      return Number(id);
    }
  }
  return null;
}
