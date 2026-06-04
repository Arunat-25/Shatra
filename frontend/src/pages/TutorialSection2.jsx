import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import TutorialLessonLayout from '../components/tutorial/TutorialLessonLayout';
import {
  allCellIdsExcept,
  BLACK_SHATRA_BATYR_CELLS,
  findBoardCellWithPiece,
  getShatraMoveTargets,
  WHITE_SHATRA_BATYR_CELLS,
} from '../components/tutorial/tutorialCells';
import { getEmptyBoard } from '../game/startingBoard';

const STEP_WHITE_PROMO = 0;
const STEP_BLACK_PROMO = 1;
const STEP_PROMO_WHITE = 2;
const STEP_PROMO_BLACK = 3;
const STEP_WIN = 4;
const STEP_DRAW = 5;
const LAST_STEP = STEP_DRAW;

const MOVE_TARGET_HINT = 'Сделайте ход на подсвеченную клетку.';

const INTERACTIVE_STEPS = {
  [STEP_PROMO_WHITE]: {
    mode: 'shatraPromote',
    startPos: 5,
    piece: 'белая шатра',
    promoteCells: WHITE_SHATRA_BATYR_CELLS,
    promoteTo: 'белый батыр',
    selectHintKey: 'tutorial.section2.promoWhiteSelectHint',
    textKey: 'tutorial.section2.step3.text',
  },
  [STEP_PROMO_BLACK]: {
    mode: 'shatraPromote',
    startPos: 58,
    piece: 'черная шатра',
    promoteCells: BLACK_SHATRA_BATYR_CELLS,
    promoteTo: 'черный батыр',
    selectHintKey: 'tutorial.section2.promoBlackSelectHint',
    textKey: 'tutorial.section2.step4.text',
  },
  [STEP_WIN]: {
    mode: 'pieceCapture',
    initialBoard: { 47: 'белый батыр', 29: 'черный бий', 56: 'белый бий' },
    piece: 'белый батыр',
    opponentPiece: 'черный бий',
    moveTargets: { 47: [17, 23] },
    captures: { 17: 29, 23: 29 },
    selectHintKey: 'tutorial.section2.winCaptureSelectHint',
    textKey: 'tutorial.section2.step5.text',
  },
};

function buildInteractiveBoard(config) {
  const b = getEmptyBoard();
  if (config.initialBoard) {
    for (const [pos, piece] of Object.entries(config.initialBoard)) {
      b[Number(pos)] = piece;
    }
    return b;
  }
  b[config.startPos] = config.piece;
  return b;
}

function boardHasPiece(board, piece) {
  return findBoardCellWithPiece(board, piece) != null;
}

export default function TutorialSection2() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState(STEP_WHITE_PROMO);

  const [demoBoard, setDemoBoard] = useState(null);
  const [stepComplete, setStepComplete] = useState(false);
  const [selected, setSelected] = useState(null);

  const interactiveConfig = INTERACTIVE_STEPS[step] ?? null;
  const isInteractiveStep = interactiveConfig != null;

  useEffect(() => {
    if (isInteractiveStep) {
      setDemoBoard(buildInteractiveBoard(interactiveConfig));
      setStepComplete(false);
      setSelected(null);
    } else {
      setDemoBoard(null);
      setSelected(null);
    }
  }, [step, isInteractiveStep, interactiveConfig]);

  const handleLessonCellClick = (id) => {
    if (!interactiveConfig || !demoBoard || stepComplete) return;

    if (interactiveConfig.mode === 'pieceCapture') {
      const { piece, opponentPiece, captures, moveTargets } = interactiveConfig;
      const pieceCell = findBoardCellWithPiece(demoBoard, piece);
      if (selected === null) {
        if (id === pieceCell) setSelected(id);
        return;
      }
      const targets = moveTargets[selected] ?? [];
      if (!targets.includes(id) || demoBoard[id]) {
        setSelected(null);
        return;
      }
      const newB = { ...demoBoard };
      newB[selected] = null;
      newB[id] = piece;
      const captured = captures[id];
      if (captured != null) newB[captured] = null;
      setDemoBoard(newB);
      setSelected(null);
      if (!boardHasPiece(newB, opponentPiece)) setStepComplete(true);
      return;
    }

    const { piece, promoteCells, promoteTo } = interactiveConfig;
    const pieceCell = findBoardCellWithPiece(demoBoard, piece);
    if (selected === null) {
      if (id === pieceCell) setSelected(id);
      return;
    }
    const targets = getShatraMoveTargets(piece, selected);
    if (!targets.includes(id) || demoBoard[id]) {
      setSelected(null);
      return;
    }
    const newB = { ...demoBoard };
    newB[selected] = null;
    if (promoteCells.includes(id)) {
      newB[id] = promoteTo;
      setStepComplete(true);
    } else {
      newB[id] = piece;
    }
    setDemoBoard(newB);
    setSelected(null);
  };

  const canProceed = isInteractiveStep ? stepComplete : true;

  const instruction = useMemo(() => {
    if (!isInteractiveStep || stepComplete) return null;
    if (selected === null) return t(interactiveConfig.selectHintKey);
    return MOVE_TARGET_HINT;
  }, [isInteractiveStep, stepComplete, selected, interactiveConfig, t]);

  const { board, tutorialDimmedCells, highlightedEssential, text } = useMemo(() => {
    if (isInteractiveStep) {
      const { piece, textKey, mode } = interactiveConfig;
      const b = demoBoard ?? buildInteractiveBoard(interactiveConfig);
      let highlights = [];
      if (!stepComplete && selected !== null) {
        highlights =
          mode === 'pieceCapture'
            ? (interactiveConfig.moveTargets[selected] ?? [])
            : getShatraMoveTargets(piece, selected);
      }
      return {
        board: b,
        tutorialDimmedCells: null,
        highlightedEssential: highlights,
        text: t(textKey),
      };
    }

    const empty = getEmptyBoard();

    if (step === STEP_WHITE_PROMO) {
      return {
        board: empty,
        tutorialDimmedCells: allCellIdsExcept(WHITE_SHATRA_BATYR_CELLS),
        highlightedEssential: WHITE_SHATRA_BATYR_CELLS,
        text: t('tutorial.section2.step1.text'),
      };
    }
    if (step === STEP_BLACK_PROMO) {
      return {
        board: empty,
        tutorialDimmedCells: allCellIdsExcept(BLACK_SHATRA_BATYR_CELLS),
        highlightedEssential: BLACK_SHATRA_BATYR_CELLS,
        text: t('tutorial.section2.step2.text'),
      };
    }
    if (step === STEP_DRAW) {
      return {
        board: empty,
        tutorialDimmedCells: null,
        highlightedEssential: [],
        text: t('tutorial.section2.step6.text'),
      };
    }

    return {
      board: empty,
      tutorialDimmedCells: null,
      highlightedEssential: [],
      text: '',
    };
  }, [step, t, demoBoard, selected, stepComplete, isInteractiveStep, interactiveConfig]);

  const handleNext = () => {
    if (step < LAST_STEP) {
      setStep(step + 1);
      return;
    }
    navigate('/tutorial');
  };

  const handleBack = () => {
    if (step > STEP_WHITE_PROMO) setStep(step - 1);
  };

  const handleTryAgain = () => {
    if (!isInteractiveStep) return;
    setDemoBoard(buildInteractiveBoard(interactiveConfig));
    setStepComplete(false);
    setSelected(null);
  };

  return (
    <TutorialLessonLayout
      board={board}
      text={text}
      tutorialDimmedCells={tutorialDimmedCells}
      highlightedEssential={highlightedEssential}
      interactive={isInteractiveStep && !stepComplete}
      onCellClick={isInteractiveStep && !stepComplete ? handleLessonCellClick : undefined}
      moveFrom={selected}
      canProceed={canProceed}
      instruction={instruction}
      onNext={handleNext}
      onBack={handleBack}
      canGoBack={step > STEP_WHITE_PROMO}
      showTryAgain={isInteractiveStep}
      onTryAgain={handleTryAgain}
    />
  );
}
