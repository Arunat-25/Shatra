import { useLayoutEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import BoardGrid from '../../BoardGrid';
import { COLOR_BLACK, COLOR_WHITE } from '../../constants';
import { getPieceColor } from '../../utils';
import {
  anchorOnRectBorderToward,
  measureCssLengthPx,
  nearestPointOnRect,
  sketchArrowPath,
  sketchCirclePath,
  SKETCH_PIECE_OUTLINE_STYLE,
  trimArrowEnds,
} from './tutorialSketchPaths';

const SHATRA_ARROW_CELLS = [1, 40];
const BIY_ARROW_CELLS = [10, 53];

const PIECE_CALLOUTS = [
  {
    cellId: 1,
    labelKey: 'tutorial.slide4.blackShatra',
    side: 'left',
    offsetX: '2cm',
    offsetY: '2cm',
    calloutId: 'shatra',
  },
  {
    cellId: 53,
    labelKey: 'tutorial.slide4.whiteBiy',
    side: 'right',
    offsetX: '-2cm',
    offsetY: '2cm',
    calloutId: 'biy',
  },
];

function relativeRect(wrapRect, el) {
  const r = el.getBoundingClientRect();
  return {
    left: r.left - wrapRect.left,
    top: r.top - wrapRect.top,
    width: r.width,
    height: r.height,
  };
}

function loupeRectAroundCell(cellRect, wrap) {
  const extra = measureCssLengthPx(wrap, '10mm');
  const size = cellRect.width * 1.22 + extra;
  const pad = (size - cellRect.width) / 2;
  const padY = (size - cellRect.height) / 2;
  return {
    left: cellRect.left - pad,
    top: cellRect.top - padY,
    width: size,
    height: size,
  };
}

function getLoupeRect(wrap, wrapRect, cell) {
  return loupeRectAroundCell(relativeRect(wrapRect, cell), wrap);
}

function squareLoupeRect(loupe) {
  const cx = loupe.left + loupe.width / 2;
  const cy = loupe.top + loupe.height / 2;
  const size = Math.min(loupe.width, loupe.height);
  return {
    left: cx - size / 2,
    top: cy - size / 2,
    width: size,
    height: size,
  };
}

function cellIdFromElement(cell) {
  return Number(cell.id.replace('position', ''));
}

function offsetLoupeByPieceColor(loupe, wrap, board, cellId) {
  const piece = board?.[cellId];
  if (!piece) return loupe;
  const color = getPieceColor(piece);
  if (color === COLOR_BLACK) {
    return { ...loupe, top: loupe.top - measureCssLengthPx(wrap, '5mm') };
  }
  if (color === COLOR_WHITE) {
    return { ...loupe, top: loupe.top + measureCssLengthPx(wrap, '3mm') };
  }
  return loupe;
}

function resolveLoupeRect(wrap, wrapRect, cell, board) {
  return offsetLoupeByPieceColor(
    squareLoupeRect(getLoupeRect(wrap, wrapRect, cell)),
    wrap,
    board,
    cellIdFromElement(cell),
  );
}

function buildLoupeToLabelArrows(wrap, wrapRect, labelEl, cells, keyPrefix, seedBase, board) {
  const labelRect = relativeRect(wrapRect, labelEl);
  return cells.map((cellId, i) => {
    const cell = wrap.querySelector(`#position${cellId}`);
    if (!cell) return null;
    const loupe = resolveLoupeRect(wrap, wrapRect, cell, board);
    const loupeCenter = {
      x: loupe.left + loupe.width / 2,
      y: loupe.top + loupe.height / 2,
    };
    const to = nearestPointOnRect(labelRect, loupeCenter.x, loupeCenter.y);
    const from = anchorOnRectBorderToward(loupe, to.x, to.y);
    return {
      key: `${keyPrefix}-${cellId}`,
      fromX: from.x,
      fromY: from.y,
      toX: to.x,
      toY: to.y,
      seed: seedBase + i,
    };
  }).filter(Boolean);
}

function applyShatraArrowTweaks(wrap, cellId, fromX, fromY, toX, toY) {
  const shiftLeft = measureCssLengthPx(wrap, '5mm');
  let fx = fromX - shiftLeft;
  let fy = fromY;
  let tx = toX - shiftLeft;
  let ty = toY;
  if (cellId === 40) {
    const trimmed = trimArrowEnds(
      fx,
      fy,
      tx,
      ty,
      measureCssLengthPx(wrap, '5mm'),
      0,
    );
    fx = trimmed.fromX;
    fy = trimmed.fromY;
    tx = trimmed.toX;
    ty = trimmed.toY;
  } else if (cellId === 1) {
    const extend = measureCssLengthPx(wrap, '5mm');
    const dx = tx - fx;
    const dy = ty - fy;
    const len = Math.hypot(dx, dy) || 1;
    fx -= (dx / len) * extend;
    fy -= (dy / len) * extend;
  }
  const endTrimmed = trimArrowEnds(fx, fy, tx, ty, 0, measureCssLengthPx(wrap, '4mm'));
  return {
    fromX: endTrimmed.fromX,
    fromY: endTrimmed.fromY,
    toX: endTrimmed.toX,
    toY: endTrimmed.toY,
  };
}

function arrowsToPaths(arrows) {
  return arrows.map(({ key, fromX, fromY, toX, toY, seed, curveBoost = 0 }) => ({
    key,
    ...sketchArrowPath(fromX, fromY, toX, toY, seed, { curveBoost }),
  }));
}

function buildLoupeOutlines(wrap, wrapRect, board) {
  return Array.from(wrap.querySelectorAll('.kletka.tutorial-spotlight')).map((cell, i) => {
    const loupe = resolveLoupeRect(wrap, wrapRect, cell, board);
    return {
      key: cell.id,
      d: sketchCirclePath(loupe, { ...SKETCH_PIECE_OUTLINE_STYLE, seed: 70 + i }),
    };
  });
}

function buildCalloutArrows(wrap, wrapRect, board) {
  const shatraEl = wrap.querySelector('[data-callout-label="shatra"]');
  const biyEl = wrap.querySelector('[data-callout-label="biy"]');
  const raw = [
    ...(shatraEl
      ? buildLoupeToLabelArrows(wrap, wrapRect, shatraEl, SHATRA_ARROW_CELLS, 'shatra-arrow', 40, board)
      : []),
    ...(biyEl
      ? buildLoupeToLabelArrows(wrap, wrapRect, biyEl, BIY_ARROW_CELLS, 'biy-arrow', 50, board)
      : []),
  ];
  const trim5 = measureCssLengthPx(wrap, '5mm');
  const adjusted = raw.map((a) => {
    if (a.key.startsWith('shatra-arrow')) {
      const cellId = Number(a.key.replace('shatra-arrow-', ''));
      const t = applyShatraArrowTweaks(wrap, cellId, a.fromX, a.fromY, a.toX, a.toY);
      return { ...a, ...t };
    }
    if (a.key.startsWith('biy-arrow')) {
      const t = trimArrowEnds(a.fromX, a.fromY, a.toX, a.toY, trim5, trim5);
      return { ...a, ...t };
    }
    return a;
  });
  return arrowsToPaths(
    adjusted.map((a) => (a.key === 'shatra-arrow-1' ? { ...a, curveBoost: -0.1 } : a)),
  );
}

export default function TutorialBoard({
  board,
  spotlightCells = null,
  showPieceCallouts = false,
}) {
  const { t } = useTranslation();
  const wrapRef = useRef(null);
  const [layout, setLayout] = useState({ callouts: [], arrows: [], loupeOutlines: [] });

  useLayoutEffect(() => {
    if (!showPieceCallouts || !wrapRef.current) {
      setLayout({ callouts: [], arrows: [], loupeOutlines: [] });
      return;
    }

    const measure = () => {
      const wrap = wrapRef.current;
      if (!wrap) return;
      const wrapRect = wrap.getBoundingClientRect();
      const callouts = PIECE_CALLOUTS.map((item) => {
        const cell = wrap.querySelector(`#position${item.cellId}`);
        if (!cell) return null;
        const r = cell.getBoundingClientRect();
        return {
          ...item,
          label: t(item.labelKey),
          cy: r.top + r.height / 2 - wrapRect.top,
        };
      }).filter(Boolean);

      setLayout((prev) => ({ callouts, arrows: prev.arrows, loupeOutlines: prev.loupeOutlines }));

      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const measuredWrapRect = wrap.getBoundingClientRect();
          setLayout({
            callouts,
            arrows: buildCalloutArrows(wrap, measuredWrapRect, board),
            loupeOutlines: buildLoupeOutlines(wrap, measuredWrapRect, board),
          });
        });
      });
    };

    measure();
    const ro = typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver(measure)
      : null;
    ro?.observe(wrapRef.current);
    window.addEventListener('resize', measure);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [showPieceCallouts, board, t]);

  const { callouts, arrows, loupeOutlines } = layout;

  return (
    <div className="tutorial-board-wrap" ref={wrapRef}>
      <div className="board board-tutorial disabled">
        <BoardGrid
          board={board}
          myColor={COLOR_WHITE}
          onCellClick={() => {}}
          interactive={false}
          spotlightCells={spotlightCells}
        />
      </div>

      {showPieceCallouts && loupeOutlines.length > 0 && (
        <svg className="tutorial-loupe-outlines" aria-hidden>
          {loupeOutlines.map((o) => (
            <path key={o.key} d={o.d} className="tutorial-sketch-outline" />
          ))}
        </svg>
      )}

      {showPieceCallouts && arrows.length > 0 && (
        <svg className="tutorial-callout-arrows" aria-hidden>
          {arrows.map((a) => (
            <g key={a.key}>
              <path d={a.shaft} className="tutorial-sketch-arrow" />
              <path d={a.head} className="tutorial-sketch-arrow" />
            </g>
          ))}
        </svg>
      )}

      {showPieceCallouts && callouts.length > 0 && (
        <div className="tutorial-callout-labels" aria-hidden>
          {callouts.map((item) => (
            <span
              key={item.cellId}
              data-callout-label={item.calloutId}
              className={`tutorial-callout-label tutorial-callout-label--${item.side}`}
              style={{
                top: item.cy,
                ...(item.side === 'left' ? { left: 4 } : { right: 4 }),
                transform: `translate(${item.offsetX}, calc(-50% + ${item.offsetY}))`,
              }}
            >
              {item.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
