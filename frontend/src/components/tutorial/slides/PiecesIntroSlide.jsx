import { useMemo } from 'react';
import { getStartingBoard } from '../../../game/startingBoard';
import TutorialBoard from '../TutorialBoard';

const SPOTLIGHT_CELLS = [1, 10, 40, 53];

export default function PiecesIntroSlide() {
  const board = useMemo(() => getStartingBoard(), []);

  return (
    <TutorialBoard
      board={board}
      spotlightCells={SPOTLIGHT_CELLS}
      showPieceCallouts
    />
  );
}
