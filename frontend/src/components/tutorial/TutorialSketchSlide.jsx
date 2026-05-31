import { useLayoutEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getEmptyBoard } from '../../game/startingBoard';
import TutorialBoard from './TutorialBoard';
import {
  anchorOnRectCorner,
  anchorOnRectEdge,
  expandFortressOutlineRect,
  expandRect,
  expandRectAxes,
  extendFortressSidesVertical,
  measureCssLengthPx,
  measureRelativeRect,
  measureZoneRects,
  mergeRelativeRects,
  offsetRectsVerticalByHalf,
  placeLabelBesideBoard,
  sketchArrowPath,
  sketchRectPath,
  trimArrowEnds,
  SKETCH_OUTLINE_PADDING,
  SKETCH_OUTLINE_STYLE,
} from './tutorialSketchPaths';

const ZONE_SELECTOR = {
  main: '.board-content .main-field',
  fortress: '.board-content .field-of-reserve',
  gate: '.board-content .field-of-king',
};

const EMPTY = getEmptyBoard();

function buildZoneLayout(wrap, zone, label) {
  const selector = ZONE_SELECTOR[zone];
  const contentRects = measureZoneRects(wrap, selector);
  if (!contentRects.length) return null;

  const boardRect = measureRelativeRect(wrap, '.board.board-tutorial');
  if (!boardRect) return null;

  const wrapSize = {
    width: wrap.getBoundingClientRect().width,
    height: wrap.getBoundingClientRect().height,
  };

  let zoneRects = contentRects;
  if (zone === 'fortress') {
    zoneRects = offsetRectsVerticalByHalf(contentRects, boardRect, wrap, {
      topMm: 5,
      bottomMm: 5,
    });
  } else if (zone === 'gate') {
    zoneRects = offsetRectsVerticalByHalf(contentRects, boardRect, wrap, {
      topMm: 6,
      bottomMm: 6,
    });
  }

  const mergedContent = mergeRelativeRects(zoneRects);
  const anchorY = mergedContent.top + mergedContent.height / 2;
  let labelPos = placeLabelBesideBoard(boardRect, wrapSize, anchorY, label);
  if (zone === 'fortress' || zone === 'gate') {
    const labelUp = measureCssLengthPx(wrap, '1.5cm');
    labelPos = {
      ...labelPos,
      top: labelPos.top - labelUp,
      anchorY: labelPos.anchorY - labelUp,
    };
  }

  const boardMid = boardRect.top + boardRect.height / 2;

  const outlines = zoneRects.map((contentRect, i) => {
    let sketchBase = contentRect;
    if (zone === 'fortress') {
      const isUpper = contentRect.top + contentRect.height / 2 < boardMid;
      const pad1 = measureCssLengthPx(wrap, '1mm');
      const padH2 = measureCssLengthPx(wrap, '2mm');
      sketchBase = expandRectAxes(
        expandFortressOutlineRect(contentRect, wrap, isUpper ? 'upper' : 'lower'),
        pad1,
        pad1,
      );
      sketchBase = expandRectAxes(sketchBase, padH2, 0);
      sketchBase = extendFortressSidesVertical(
        sketchBase,
        wrap,
        isUpper ? 'upper' : 'lower',
      );
    }
    const outer = expandRect(sketchBase, SKETCH_OUTLINE_PADDING);
    return {
      key: `${zone}-${i}`,
      d: sketchRectPath(outer, { padding: 0, ...SKETCH_OUTLINE_STYLE, seed: 10 + i }),
      outer,
      contentRect,
    };
  });

  const arrows = outlines.map((item, i) => {
    const isUpperZone =
      item.contentRect.top + item.contentRect.height / 2 < boardMid;
    let fromSide = labelPos.placement === 'below' ? 'bottom' : 'right';
    if (zone === 'fortress' && labelPos.placement === 'below' && !isUpperZone) {
      fromSide = 'left';
    }
    const targetY = item.contentRect.top + item.contentRect.height / 2;
    let toX = labelPos.anchorX;
    let toY = labelPos.placement === 'below' ? labelPos.anchorY : targetY;
    let fromX;
    let fromY;
    if (zone === 'gate') {
      const corner = anchorOnRectCorner(item.outer, 'bottom-left');
      fromX = corner.x;
      fromY = corner.y;
    } else {
      const from = anchorOnRectEdge(item.outer, fromSide);
      fromX = from.x;
      fromY = from.y;
    }
    if (zone === 'fortress' && isUpperZone) {
      fromX -= measureCssLengthPx(wrap, '1cm');
    }
    if (zone === 'fortress' || zone === 'gate') {
      const startTrim =
        zone === 'gate' ? measureCssLengthPx(wrap, '1cm') : measureCssLengthPx(wrap, '5mm');
      let endTrim = isUpperZone
        ? measureCssLengthPx(wrap, '1cm')
        : measureCssLengthPx(wrap, '3cm');
      if (zone === 'fortress' && isUpperZone) {
        endTrim += measureCssLengthPx(wrap, '2mm');
      }
      const trimmed = trimArrowEnds(fromX, fromY, toX, toY, startTrim, endTrim);
      fromX = trimmed.fromX;
      fromY = trimmed.fromY;
      toX = trimmed.toX;
      toY = trimmed.toY;
      if (zone === 'gate') {
        const extendStart = measureCssLengthPx(wrap, '0.5cm');
        const dx = toX - fromX;
        const dy = toY - fromY;
        const len = Math.hypot(dx, dy) || 1;
        fromX -= (dx / len) * extendStart;
        fromY -= (dy / len) * extendStart;
      } else if (zone === 'fortress' && !isUpperZone) {
        fromY -= measureCssLengthPx(wrap, '1cm');
      }
      if (isUpperZone) {
        toX += measureCssLengthPx(wrap, '8mm');
        if (zone === 'fortress') {
          const extendEnd = measureCssLengthPx(wrap, '0.5cm');
          const dx = toX - fromX;
          const dy = toY - fromY;
          const len = Math.hypot(dx, dy) || 1;
          toX += (dx / len) * extendEnd;
          toY += (dy / len) * extendEnd;
        } else if (zone === 'gate') {
          const extendEnd = measureCssLengthPx(wrap, '1mm');
          const dx = toX - fromX;
          const dy = toY - fromY;
          const len = Math.hypot(dx, dy) || 1;
          toX += (dx / len) * extendEnd;
          toY += (dy / len) * extendEnd;
        }
      } else {
        const endAdj = measureCssLengthPx(wrap, '0.7mm');
        for (let n = 0; n < 2; n += 1) {
          toY -= endAdj;
          const dx = toX - fromX;
          const dy = toY - fromY;
          const len = Math.hypot(dx, dy) || 1;
          toX += (dx / len) * endAdj;
          toY += (dy / len) * endAdj;
        }
        if (zone === 'fortress') {
          toY -= measureCssLengthPx(wrap, '0.5mm');
          toY -= measureCssLengthPx(wrap, '1cm');
          toY += measureCssLengthPx(wrap, '0.5cm');
          const extendEnd = measureCssLengthPx(wrap, '1cm');
          const dx = toX - fromX;
          const dy = toY - fromY;
          const len = Math.hypot(dx, dy) || 1;
          toX += (dx / len) * extendEnd;
          toY += (dy / len) * extendEnd;
        } else if (zone === 'gate') {
          toY += measureCssLengthPx(wrap, '3mm');
          const extendEnd = measureCssLengthPx(wrap, '5mm');
          const dx = toX - fromX;
          const dy = toY - fromY;
          const len = Math.hypot(dx, dy) || 1;
          toX += (dx / len) * extendEnd;
          toY += (dy / len) * extendEnd;
        }
      }
    }
    let curveBoost = 0;
    if (!isUpperZone && (zone === 'fortress' || zone === 'gate')) {
      curveBoost = -0.1;
    }
    return {
      ...sketchArrowPath(fromX, fromY, toX, toY, 20 + i, { curveBoost }),
      key: `arrow-${i}`,
    };
  });

  return {
    label,
    labelPos,
    outlines: outlines.map(({ key, d }) => ({ key, d })),
    arrows,
  };
}

export default function TutorialSketchSlide({ zone, labelKey }) {
  const { t } = useTranslation();
  const wrapRef = useRef(null);
  const [layout, setLayout] = useState(null);

  useLayoutEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;

    const measure = () => {
      setLayout(buildZoneLayout(wrap, zone, t(labelKey)));
    };

    measure();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null;
    ro?.observe(wrap);
    window.addEventListener('resize', measure);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [zone, labelKey, t]);

  return (
    <div className="tutorial-sketch-slide" ref={wrapRef}>
      <TutorialBoard board={EMPTY} />
      {layout && (
        <>
          <svg className="tutorial-sketch-layer" aria-hidden>
            {layout.outlines.map((o) => (
              <path key={o.key} d={o.d} className="tutorial-sketch-outline" />
            ))}
            {layout.arrows.map((a) => (
              <g key={a.key}>
                <path d={a.shaft} className="tutorial-sketch-arrow" />
                <path d={a.head} className="tutorial-sketch-arrow" />
              </g>
            ))}
          </svg>
          <span
            className={
              zone === 'fortress' || zone === 'gate'
                ? 'tutorial-sketch-label tutorial-sketch-label--plain'
                : 'tutorial-sketch-label'
            }
            style={{
              left: layout.labelPos.left,
              top: layout.labelPos.top,
              transform: layout.labelPos.transform,
              textAlign: layout.labelPos.textAlign,
            }}
          >
            {layout.label}
          </span>
        </>
      )}
    </div>
  );
}
