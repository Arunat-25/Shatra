import { getBoardSections } from '../constants';

const BOARD_PADDING = 3;
const TOP_INSET = 5;

/**
 * Mirror CSS --board-unit / --cell-size / --reserve-cell-size from game-mobile.css.
 */
export function computeBoardLayout(myColor, width, height) {
  const sections = getBoardSections(myColor);
  const innerW = Math.max(0, width - BOARD_PADDING * 2);
  const innerH = Math.max(0, height - BOARD_PADDING * 2);
  const unit = Math.max(0, Math.min((innerH - 10) / 13.6, (innerW - 10) / 7));
  const cellSize = unit;
  const reserveSize = unit * 0.86;
  const gateGap = unit * 0.08;

  const cells = {};
  let y = BOARD_PADDING + TOP_INSET;
  const centerX = width / 2;
  let isFirstSection = true;

  for (const section of sections) {
    const isReserve = section.class === 'field-of-reserve';
    const isKing = section.class === 'field-of-king';
    const rowCellSize = isReserve ? reserveSize : cellSize;

    if (isKing && !isFirstSection) {
      y += gateGap;
    }
    isFirstSection = false;

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
        };
        x += rowCellSize;
      }
      y += rowCellSize;
    }
  }

  return {
    cells,
    cellSize,
    reserveSize,
    width,
    height,
    contentHeight: y + BOARD_PADDING,
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
