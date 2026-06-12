import '../styles/tutorial.css';
import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import TutorialLessonLayout from '../components/tutorial/TutorialLessonLayout';
import {
  allCellIdsExcept,
  BLACK_FORTRESS_CELL_IDS,
  BLACK_GATE_CELL_IDS,
  MAIN_FIELD_CELL_IDS,
  WHITE_GATE_CELL_IDS,
  WHITE_FORTRESS_CELL_IDS,
} from '../components/tutorial/tutorialCells';
import { getEmptyBoard, getStartingBoard } from '../game/startingBoard';

const STEP_FORTRESS = 1;
const STEP_GATE = 2;
const STEP_MAIN_FIELD = 3;
const STEP_WHITE_GATE = 4;
const STEP_WHITE_FORTRESS = 5;
const STEP_PIECES_OVERVIEW = 6;
const STEP_SHATRA_TYPE = 7;
const STEP_BIY_TYPE = 8;
const STEP_BATYR_TYPE = 9;
const STEP_SHATRA_MOVE = 10;
const STEP_BIY_MOVE = 11;
const STEP_BATYR_MOVE = 12;
const STEP_STARTING_POSITION = 13;

const SHOWCASE_WHITE_SHATRA = 43;
const SHOWCASE_BLACK_SHATRA = 27;
const SHOWCASE_WHITE_BIY = 20;
const SHOWCASE_BLACK_BIY = 16;
const SHOWCASE_WHITE_BATYR = 48;
const SHOWCASE_BLACK_BATYR = 15;

const INTERACTIVE_MOVE_STEPS = {
  [STEP_SHATRA_MOVE]: {
    pos: 43,
    piece: 'белая шатра',
    targets: [44, 42, 37, 36, 35],
    selectHint: 'Кликните на белую шатру, чтобы выбрать её и увидеть возможные ходы.',
    textKey: 'tutorial.section1.step11.text',
  },
  [STEP_BIY_MOVE]: {
    pos: 20,
    piece: 'белый бий',
    targets: [12, 13, 14, 19, 21, 26, 27, 28],
    selectHint: 'Кликните на белого бия, чтобы выбрать его и увидеть возможные ходы.',
    textKey: 'tutorial.section1.step12.text',
  },
  [STEP_BATYR_MOVE]: {
    pos: 48,
    piece: 'белый батыр',
    targets: [13, 20, 24, 27, 30, 32, 34, 36, 40, 41, 42, 46, 47, 49, 50, 51, 52, 53, 56],
    selectHint: 'Кликните на белого батыра, чтобы выбрать его и увидеть возможные ходы.',
    textKey: 'tutorial.section1.step13.text',
  },
};

const MOVE_TARGET_HINT = 'Выберите одну из подсвеченных клеток, чтобы сделать ход.';

function buildInteractiveBoard(step) {
  const config = INTERACTIVE_MOVE_STEPS[step];
  if (!config) return null;
  const b = getEmptyBoard();
  b[config.pos] = config.piece;
  return b;
}

function buildPieceShowcaseBoard() {
  const b = getEmptyBoard();
  b[SHOWCASE_WHITE_SHATRA] = 'белая шатра';
  b[SHOWCASE_BLACK_SHATRA] = 'черная шатра';
  b[SHOWCASE_WHITE_BIY] = 'белый бий';
  b[SHOWCASE_BLACK_BIY] = 'черный бий';
  b[SHOWCASE_WHITE_BATYR] = 'белый батыр';
  b[SHOWCASE_BLACK_BATYR] = 'черный батыр';
  return b;
}

export default function TutorialSection1() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const [demoBoard, setDemoBoard] = useState(null);
  const [moveDone, setMoveDone] = useState(false);
  const [selected, setSelected] = useState(null);

  const interactiveConfig = INTERACTIVE_MOVE_STEPS[step] ?? null;
  const isInteractiveStep = interactiveConfig != null;

  useEffect(() => {
    if (isInteractiveStep) {
      setDemoBoard(buildInteractiveBoard(step));
      setMoveDone(false);
      setSelected(null);
    } else {
      setDemoBoard(null);
      setSelected(null);
    }
  }, [step, isInteractiveStep]);

  const handleLessonCellClick = (id) => {
    if (!interactiveConfig || !demoBoard || moveDone) return;
    const { pos, targets } = interactiveConfig;
    if (selected === null) {
      if (id === pos) setSelected(id);
      return;
    }
    if (targets.includes(id) && !demoBoard[id]) {
      const newB = { ...demoBoard };
      newB[id] = newB[selected];
      newB[selected] = null;
      setDemoBoard(newB);
      setMoveDone(true);
      setSelected(null);
    } else {
      setSelected(null);
    }
  };

  const canProceed = isInteractiveStep ? moveDone : true;
  const instruction =
    isInteractiveStep && !moveDone
      ? (selected ? MOVE_TARGET_HINT : interactiveConfig.selectHint)
      : null;

  const { board, tutorialDimmedCells, highlightedEssential, text } = useMemo(() => {
    if (step === STEP_STARTING_POSITION) {
      return {
        board: getStartingBoard(),
        tutorialDimmedCells: null,
        highlightedEssential: [],
        text: t('tutorial.section1.step14.text'),
      };
    }

    if (isInteractiveStep) {
      const { targets, textKey } = interactiveConfig;
      const b = demoBoard ?? buildInteractiveBoard(step);
      const currentHighlights = selected !== null && !moveDone ? targets : [];
      return {
        board: b,
        tutorialDimmedCells: null,
        highlightedEssential: currentHighlights,
        text: t(textKey),
      };
    }

    const empty = getEmptyBoard();
    let dimmed = null;
    let txt;

    if (step === STEP_BATYR_TYPE) {
      txt = t('tutorial.section1.step10.text');
      const keep = [SHOWCASE_WHITE_BATYR, SHOWCASE_BLACK_BATYR];
      return {
        board: buildPieceShowcaseBoard(),
        tutorialDimmedCells: allCellIdsExcept(keep),
        highlightedEssential: [],
        text: txt,
      };
    }
    if (step === STEP_BIY_TYPE) {
      txt = t('tutorial.section1.step9.text');
      const keep = [SHOWCASE_WHITE_BIY, SHOWCASE_BLACK_BIY];
      return {
        board: buildPieceShowcaseBoard(),
        tutorialDimmedCells: allCellIdsExcept(keep),
        highlightedEssential: [],
        text: txt,
      };
    }
    if (step === STEP_SHATRA_TYPE) {
      txt = t('tutorial.section1.step8.text');
      const keep = [SHOWCASE_WHITE_SHATRA, SHOWCASE_BLACK_SHATRA];
      return {
        board: buildPieceShowcaseBoard(),
        tutorialDimmedCells: allCellIdsExcept(keep),
        highlightedEssential: [],
        text: txt,
      };
    }
    if (step === STEP_PIECES_OVERVIEW) {
      txt = t('tutorial.section1.step7.text');
      return {
        board: buildPieceShowcaseBoard(),
        tutorialDimmedCells: null,
        highlightedEssential: [],
        text: txt,
      };
    }
    if (step === STEP_WHITE_FORTRESS) {
      dimmed = allCellIdsExcept(WHITE_FORTRESS_CELL_IDS);
      txt = t('tutorial.section1.step6.text');
    } else if (step === STEP_WHITE_GATE) {
      dimmed = allCellIdsExcept(WHITE_GATE_CELL_IDS);
      txt = t('tutorial.section1.step5.text');
    } else if (step === STEP_MAIN_FIELD) {
      dimmed = allCellIdsExcept(MAIN_FIELD_CELL_IDS);
      txt = t('tutorial.section1.step4.text');
    } else if (step === STEP_GATE) {
      dimmed = allCellIdsExcept(BLACK_GATE_CELL_IDS);
      txt = t('tutorial.section1.step3.text');
    } else if (step === STEP_FORTRESS) {
      dimmed = allCellIdsExcept(BLACK_FORTRESS_CELL_IDS);
      txt = t('tutorial.section1.step2.text');
    } else {
      txt = t('tutorial.section1.step1.text');
    }

    return {
      board: empty,
      tutorialDimmedCells: dimmed,
      highlightedEssential: [],
      text: txt,
    };
  }, [step, t, demoBoard, selected, moveDone, isInteractiveStep, interactiveConfig]);

  const handleNext = () => {
    if (step < STEP_STARTING_POSITION) {
      setStep(step + 1);
      return;
    }
    navigate('/tutorial');
  };

  const handleBack = () => {
    if (step > 0) setStep(step - 1);
  };

  const handleTryAgain = () => {
    if (!isInteractiveStep) return;
    setDemoBoard(buildInteractiveBoard(step));
    setMoveDone(false);
    setSelected(null);
  };

  const interactive = isInteractiveStep && !moveDone;

  return (
    <TutorialLessonLayout
      board={board}
      text={text}
      tutorialDimmedCells={tutorialDimmedCells}
      highlightedEssential={highlightedEssential}
      interactive={interactive}
      onCellClick={interactive ? handleLessonCellClick : undefined}
      moveFrom={selected}
      canProceed={canProceed}
      instruction={instruction}
      onNext={handleNext}
      onBack={handleBack}
      canGoBack={step > 0}
      showTryAgain={isInteractiveStep}
      onTryAgain={handleTryAgain}
    />
  );
}
