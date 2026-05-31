import { useLayoutEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getEmptyBoard } from '../../../game/startingBoard';
import TutorialBoard from '../TutorialBoard';
import {
  expandRectAxes,
  measureZoneRects,
  mergeRelativeRects,
  measureRelativeRect,
  offsetGateRectsVertical,
  sketchArrowPath,
  sketchRectPath,
  trimArrowEnds,
} from '../tutorialSketchPaths';

const EMPTY = getEmptyBoard();
const LABEL_OFFSET_X_CM = -4;
const LABEL_OFFSET_Y_CM = 1;

function cssLengthToPx(wrapEl, length) {
  const probe = document.createElement('div');
  probe.style.cssText = 'position:absolute;visibility:hidden;pointer-events:none';
  probe.style.width = length;
  wrapEl.appendChild(probe);
  const px = probe.getBoundingClientRect().width;
  probe.remove();
  return px;
}

function cmToPx(wrapEl, cm) {
  const px = cssLengthToPx(wrapEl, `${Math.abs(cm)}cm`);
  return cm < 0 ? -px : px;
}

function buildMainFieldLayout(wrap, labelText) {
  const mainRects = measureZoneRects(wrap, '.board-content .main-field');
  const boardRect = measureRelativeRect(wrap, '.board.board-tutorial');
  let gateRects = measureZoneRects(wrap, '.board-content .field-of-king');
  if (boardRect) {
    gateRects = offsetGateRectsVertical(gateRects, boardRect, wrap);
  }
  const merged = mergeRelativeRects([...mainRects, ...gateRects]);
  if (!merged) return null;

  const sampleCell = wrap.querySelector('.main-field .kletka');
  const cellW = sampleCell?.getBoundingClientRect().width ?? 0;
  const padY = 3;
  const padX = Math.max(10, cellW * 0.95);

  const outerExpanded = expandRectAxes(merged, padX, padY);
  const trimSides = cssLengthToPx(wrap, '8mm');
  const trimEnds = cssLengthToPx(wrap, '5mm');
  const trimMore = cssLengthToPx(wrap, '1mm');
  const outer = {
    left: outerExpanded.left,
    top: outerExpanded.top + trimSides / 2 + trimEnds + trimMore,
    width: outerExpanded.width,
    height: outerExpanded.height - trimSides - trimEnds * 2 - trimMore * 2,
  };
  const outlinePath = sketchRectPath(outer, {
    padding: 0,
    wobble: 3.2,
    curve: 1.2,
    steps: 22,
    seed: 1,
  });

  const wrapRect = wrap.getBoundingClientRect();
  const margin = 8;
  const estLabelH = 28;
  const estLabelW = Math.min(130, labelText.length * 7.5 + 20);

  let labelLeft = wrapRect.width - margin - estLabelW;
  let labelTop = margin;

  if (boardRect) {
    if (labelLeft + estLabelW > boardRect.left - 6) {
      labelLeft = Math.max(margin, boardRect.right + 10);
    }
    if (labelTop + estLabelH > boardRect.top - 4) {
      labelTop = margin;
    }
  }

  const labelAnchorX = labelLeft + cmToPx(wrap, LABEL_OFFSET_X_CM);
  const labelAnchorY = labelTop + estLabelH / 2 + cmToPx(wrap, LABEL_OFFSET_Y_CM);

  const fromX = outer.left + outer.width - cmToPx(wrap, 2);
  const fromY = Math.min(outer.top + outer.height - 1, Math.max(outer.top + 1, labelAnchorY));
  const toX = labelAnchorX + cmToPx(wrap, 2);
  const toY = labelAnchorY;
  const trimmed = trimArrowEnds(
    fromX,
    fromY,
    toX,
    toY,
    cssLengthToPx(wrap, '6mm'),
    cssLengthToPx(wrap, '2mm'),
  );
  const arrowDown = cssLengthToPx(wrap, '1mm');
  const arrow = sketchArrowPath(
    trimmed.fromX,
    trimmed.fromY + arrowDown,
    trimmed.toX,
    trimmed.toY + arrowDown,
    3,
  );

  return {
    outlinePath,
    arrow,
    label: labelText,
    labelPos: { left: labelLeft, top: labelTop },
  };
}

export default function MainFieldSlide() {
  const { t } = useTranslation();
  const wrapRef = useRef(null);
  const [layout, setLayout] = useState(null);

  useLayoutEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;

    const measure = () => {
      setLayout(buildMainFieldLayout(wrap, t('tutorial.slide1.mainField')));
    };

    measure();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(measure) : null;
    ro?.observe(wrap);
    window.addEventListener('resize', measure);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', measure);
    };
  }, [t]);

  return (
    <div className="tutorial-sketch-slide" ref={wrapRef}>
      <TutorialBoard board={EMPTY} />
      {layout && (
        <>
          <svg className="tutorial-sketch-layer" aria-hidden>
            <path d={layout.outlinePath} className="tutorial-sketch-outline" />
            <g>
              <path d={layout.arrow.shaft} className="tutorial-sketch-arrow" />
              <path d={layout.arrow.head} className="tutorial-sketch-arrow" />
            </g>
          </svg>
          <span
            className="tutorial-sketch-label tutorial-sketch-label--plain"
            style={{
              left: layout.labelPos.left,
              top: layout.labelPos.top,
              transform: `translate(${LABEL_OFFSET_X_CM}cm, ${LABEL_OFFSET_Y_CM}cm)`,
            }}
          >
            {layout.label}
          </span>
        </>
      )}
    </div>
  );
}
