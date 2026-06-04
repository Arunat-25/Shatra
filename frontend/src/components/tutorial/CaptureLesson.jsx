import { useMemo, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import TutorialLessonLayout from './TutorialLessonLayout';
import {
  buildCaptureBoard,
  buildChainCapturedGhosts,
  getAllowedTargets,
  getChainForStart,
  getChainMap,
  getNextChainHop,
  getStepPieces,
} from './captureLessonHelpers';

function resetChainState(setters) {
  setters.setChainHistory([]);
  setters.setChainStart(null);
  setters.setCaptureDone(false);
  setters.setSelected(null);
}

export default function CaptureLesson({
  steps,
  lastStepIndex,
  finishPath = '/tutorial',
  onBackFromStart,
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);

  const config = steps[step];
  const chainMap = getChainMap(config);
  const isChainStep = Boolean(chainMap);
  const [chainHistory, setChainHistory] = useState([]);
  const [chainStart, setChainStart] = useState(null);

  const stepPieces = useMemo(
    () => getStepPieces(config, chainStart, chainHistory),
    [config, chainStart, chainHistory],
  );

  const [demoBoard, setDemoBoard] = useState(() => buildCaptureBoard(steps, 0, [], null));
  const [captureDone, setCaptureDone] = useState(false);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    setDemoBoard(buildCaptureBoard(steps, step, [], null));
    setChainHistory([]);
    setChainStart(null);
    setCaptureDone(false);
    setSelected(null);
  }, [step, steps]);

  const handleLessonCellClick = (id) => {
    if (captureDone) return;

    if (selected === null) {
      if (stepPieces[id]) {
        setSelected(id);
        if (isChainStep && chainStart == null) setChainStart(id);
      }
      return;
    }

    const pieceConfig = stepPieces[selected];
    const targets = getAllowedTargets(pieceConfig);
    const capturedCell = pieceConfig.captures?.[id];
    if (targets.includes(id) && !demoBoard[id]) {
      if (isChainStep) {
        const newHistory = [...chainHistory, id];
        setChainHistory(newHistory);
        setDemoBoard(buildCaptureBoard(steps, step, newHistory, chainStart));
        const chain = getChainForStart(chainMap, chainStart);
        const nextHop = chain ? getNextChainHop(chain, newHistory) : null;
        if (nextHop) {
          setSelected(nextHop.piecePos);
        } else {
          setCaptureDone(true);
          setSelected(null);
        }
      } else {
        const newB = { ...demoBoard };
        newB[id] = newB[selected];
        newB[selected] = null;
        if (capturedCell != null) newB[capturedCell] = null;
        setDemoBoard(newB);
        setCaptureDone(true);
        setSelected(null);
      }
    } else {
      setSelected(null);
      if (isChainStep && chainHistory.length === 0) {
        setChainStart(null);
        setDemoBoard(buildCaptureBoard(steps, step, [], null));
      }
    }
  };

  const handleTryAgain = () => {
    setDemoBoard(buildCaptureBoard(steps, step, [], null));
    setChainHistory([]);
    setChainStart(null);
    setCaptureDone(false);
    setSelected(null);
  };

  const highlightedEssential = useMemo(() => {
    if (selected === null || captureDone) return [];
    return getAllowedTargets(stepPieces[selected]);
  }, [selected, captureDone, stepPieces]);

  const capturedGhostPieces = useMemo(
    () => buildChainCapturedGhosts(config, chainHistory, captureDone, chainStart),
    [config, chainHistory, captureDone, chainStart],
  );

  const canPassTurn = useMemo(() => {
    if (!config.allowPassTurn || captureDone || chainHistory.length === 0) return false;
    const chain = getChainForStart(chainMap, chainStart);
    return Boolean(chain && getNextChainHop(chain, chainHistory));
  }, [config.allowPassTurn, captureDone, chainHistory, chainMap, chainStart]);

  const hint = (keyName, raw) => (config[keyName] ? t(config[keyName]) : raw);

  const instruction = useMemo(() => {
    if (captureDone) return null;
    if (selected === null) return hint('selectHintKey', config.selectHint);
    if (isChainStep && chainHistory.length > 0) {
      return hint('chainContinueHintKey', config.chainContinueHint);
    }
    const targets = selected != null ? getAllowedTargets(stepPieces[selected]) : [];
    if (targets.length === 0) {
      return hint('noMovesHintKey', config.noMovesHint);
    }
    return hint('targetHintKey', config.targetHint);
  }, [captureDone, selected, config, isChainStep, chainHistory.length, stepPieces, t]);

  const interactive = !captureDone;

  const handlePassTurn = () => {
    setCaptureDone(true);
    setSelected(null);
  };

  const handleNext = () => {
    resetChainState({
      setChainHistory,
      setChainStart,
      setCaptureDone,
      setSelected,
    });
    if (step < lastStepIndex) {
      setStep(step + 1);
      return;
    }
    navigate(finishPath);
  };

  const handleBack = () => {
    if (step > 0) {
      resetChainState({
        setChainHistory,
        setChainStart,
        setCaptureDone,
        setSelected,
      });
      setStep(step - 1);
      return;
    }
    onBackFromStart?.();
  };

  return (
    <TutorialLessonLayout
      board={demoBoard}
      text={t(config.textKey)}
      highlightedEssential={highlightedEssential}
      highlightedCaptured={[]}
      capturedGhostPieces={capturedGhostPieces}
      interactive={interactive}
      onCellClick={interactive ? handleLessonCellClick : undefined}
      moveFrom={selected}
      canProceed={captureDone}
      instruction={instruction}
      showPassTurn={canPassTurn}
      onPassTurn={handlePassTurn}
      onNext={handleNext}
      onBack={handleBack}
      canGoBack={step > 0 || Boolean(onBackFromStart)}
      showTryAgain
      onTryAgain={handleTryAgain}
    />
  );
}
