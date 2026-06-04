import { useMemo, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import TutorialLessonLayout from '../components/tutorial/TutorialLessonLayout';
import CaptureLesson from '../components/tutorial/CaptureLesson';
import {
  buildFortressCaptureBoard,
  buildFortressLessonBoard,
  canFortressCaptureFrom,
  FORTRESS_BIY_BATYR_STEP,
  getBlackBiyCellAfterDeploy,
  getDeployTargets,
  getFortressCaptureTargets,
  getMainFieldShatraTargets,
  getNextDeployCell,
  isFortressCell,
  isMainFieldWhiteShatra,
} from '../components/tutorial/fortressLessonHelpers';

const DEPLOY_STEP = 0;
const CAPTURE_STEP = 1;
const BIY_BATYR_STEP = 2;

export default function TutorialSection5() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [lessonStep, setLessonStep] = useState(DEPLOY_STEP);

  const [deployments, setDeployments] = useState([]);
  const [deploySelected, setDeploySelected] = useState(null);
  const [deployInstructionKey, setDeployInstructionKey] = useState('tutorial.section5.deployHint');

  const [captureResult, setCaptureResult] = useState(null);
  const [captureSelected, setCaptureSelected] = useState(null);
  const [captureInstructionKey, setCaptureInstructionKey] = useState(
    'tutorial.section5.captureSelectHint',
  );

  const deployComplete = deployments.length >= 9;
  const blackBiyCell = getBlackBiyCellAfterDeploy(deployments.length);
  const deployBoard = useMemo(
    () => buildFortressLessonBoard(deployments, blackBiyCell),
    [deployments, blackBiyCell],
  );
  const nextDeployCell = useMemo(() => getNextDeployCell(deployBoard), [deployBoard]);

  const captureBoard = useMemo(() => buildFortressCaptureBoard(captureResult), [captureResult]);
  const captureDone = captureResult != null;

  const isDeployStep = lessonStep === DEPLOY_STEP;
  const board = isDeployStep ? deployBoard : captureBoard;
  const canProceed = isDeployStep ? deployComplete : captureDone;

  const deployHighlights = useMemo(() => {
    if (!isDeployStep || !deploySelected) return [];
    if (deploySelected === nextDeployCell) {
      return getDeployTargets(deployBoard, deploySelected);
    }
    if (isMainFieldWhiteShatra(deployBoard, deploySelected)) {
      return getMainFieldShatraTargets(deployBoard, deploySelected);
    }
    return [];
  }, [isDeployStep, deploySelected, deployComplete, deployBoard, nextDeployCell]);

  const captureHighlights = useMemo(() => {
    if (isDeployStep || !captureSelected || captureDone) return [];
    if (canFortressCaptureFrom(captureSelected)) {
      return getFortressCaptureTargets(captureSelected);
    }
    return [];
  }, [isDeployStep, captureSelected, captureDone]);

  const highlightedEssential = isDeployStep ? deployHighlights : captureHighlights;
  const selected = isDeployStep ? deploySelected : captureSelected;

  const applyDeployInstruction = useCallback((key) => {
    setDeployInstructionKey(key);
  }, []);

  const handleDeployCellClick = (id) => {
    if (deployComplete) return;

    if (deploySelected === null) {
      if (id === nextDeployCell && deployBoard[id]) {
        setDeploySelected(id);
        applyDeployInstruction('tutorial.section5.deployTargetHint');
        return;
      }
      if (isMainFieldWhiteShatra(deployBoard, id)) {
        setDeploySelected(id);
        applyDeployInstruction('tutorial.section5.mainFieldBlockedHint');
        return;
      }
      if (isFortressCell(id) && deployBoard[id]?.includes('белая шатра')) {
        applyDeployInstruction('tutorial.section5.fortressOrderHint');
        return;
      }
      if (isFortressCell(id)) {
        applyDeployInstruction('tutorial.section5.fortressNoMoveHint');
      }
      return;
    }

    if (deploySelected === nextDeployCell) {
      const targets = getDeployTargets(deployBoard, deploySelected);
      if (targets.includes(id)) {
        setDeployments([...deployments, { from: deploySelected, to: id }]);
        setDeploySelected(null);
        applyDeployInstruction('tutorial.section5.deployHint');
        return;
      }
    }

    if (isMainFieldWhiteShatra(deployBoard, deploySelected)) {
      const targets = getMainFieldShatraTargets(deployBoard, deploySelected);
      setDeploySelected(null);
      applyDeployInstruction(
        targets.includes(id)
          ? 'tutorial.section5.mainFieldBlockedHint'
          : 'tutorial.section5.deployHint',
      );
      return;
    }

    setDeploySelected(null);
    applyDeployInstruction('tutorial.section5.deployHint');
  };

  const handleCaptureCellClick = (id) => {
    if (captureDone) return;

    if (captureSelected === null) {
      if (canFortressCaptureFrom(id)) {
        setCaptureSelected(id);
        setCaptureInstructionKey('tutorial.section5.captureTargetHint');
        return;
      }
      if (isFortressCell(id) && captureBoard[id]?.includes('белая шатра')) {
        setCaptureInstructionKey('tutorial.section5.captureWrongPieceHint');
      }
      return;
    }

    if (canFortressCaptureFrom(captureSelected)) {
      const targets = getFortressCaptureTargets(captureSelected);
      if (targets.includes(id)) {
        setCaptureResult({ from: captureSelected, to: id });
        setCaptureSelected(null);
        setCaptureInstructionKey('tutorial.section5.captureAfterHint');
        return;
      }
    }

    setCaptureSelected(null);
    setCaptureInstructionKey('tutorial.section5.captureSelectHint');
  };

  const handleLessonCellClick = (id) => {
    if (isDeployStep) {
      handleDeployCellClick(id);
    } else {
      handleCaptureCellClick(id);
    }
  };

  const handleTryAgain = () => {
    if (isDeployStep) {
      setDeployments([]);
      setDeploySelected(null);
      setDeployInstructionKey('tutorial.section5.deployHint');
      return;
    }
    setCaptureResult(null);
    setCaptureSelected(null);
    setCaptureInstructionKey('tutorial.section5.captureSelectHint');
  };

  const handleNext = () => {
    if (isDeployStep && deployComplete) {
      setLessonStep(CAPTURE_STEP);
      return;
    }
    if (!isDeployStep && captureDone) {
      setLessonStep(BIY_BATYR_STEP);
    }
  };

  const handleBack = () => {
    if (lessonStep > DEPLOY_STEP) {
      setLessonStep(DEPLOY_STEP);
      setCaptureResult(null);
      setCaptureSelected(null);
      setCaptureInstructionKey('tutorial.section5.captureSelectHint');
      return;
    }
    navigate('/tutorial');
  };

  const textKey = isDeployStep ? 'tutorial.section5.step1.text' : 'tutorial.section5.step2.text';
  const instruction = useMemo(() => {
    if (!isDeployStep && captureResult) {
      return t('tutorial.section5.captureAfterHint', { cell: captureResult.to });
    }
    if (canProceed) return null;
    return t(isDeployStep ? deployInstructionKey : captureInstructionKey, { cell: nextDeployCell });
  }, [
    isDeployStep,
    captureResult,
    canProceed,
    deployInstructionKey,
    captureInstructionKey,
    nextDeployCell,
    t,
  ]);

  if (lessonStep === BIY_BATYR_STEP) {
    return (
      <CaptureLesson
        steps={FORTRESS_BIY_BATYR_STEP}
        lastStepIndex={3}
        onBackFromStart={() => setLessonStep(CAPTURE_STEP)}
      />
    );
  }

  return (
    <TutorialLessonLayout
      board={board}
      text={t(textKey)}
      highlightedEssential={highlightedEssential}
      interactive={!canProceed}
      onCellClick={canProceed ? undefined : handleLessonCellClick}
      moveFrom={selected}
      canProceed={canProceed}
      instruction={instruction}
      onNext={handleNext}
      onBack={handleBack}
      canGoBack
      showTryAgain
      onTryAgain={handleTryAgain}
    />
  );
}
