import '../styles/tutorial.css';
import CaptureLesson from '../components/tutorial/CaptureLesson';

const STEPS = {
  0: {
    piecePos: 27,
    piece: 'белая шатра',
    blackCells: [20, 33, 35, 39],
    captureLandings: { 13: 20, 43: 35 },
    selectHint: 'Кликните на белую шатру, чтобы увидеть, какие взятия возможны.',
    targetHint:
      'Кликните на подсвеченную клетку за фигурой соперника — шатра перепрыгнет и снимет её.',
    textKey: 'tutorial.section3.step1.text',
  },
  1: {
    piecePos: 24,
    piece: 'белый батыр',
    blackCells: [52, 31, 20],
    captureLandings: { 18: 20, 19: 20, 38: 31, 45: 31 },
    selectHint: 'Кликните на белого батыра, чтобы увидеть, какие взятия возможны.',
    targetHint:
      'Кликните на подсвеченную клетку за фигурой соперника — батыр перепрыгнет и снимет её.',
    textKey: 'tutorial.section3.step2.text',
  },
  2: {
    piecePos: 11,
    piece: 'белый бий',
    blackCells: [12],
    whiteShatraCells: [43],
    allowedTargets: [13, 18, 19],
    captureLandings: { 13: 12 },
    selectHint: 'Кликните на белого бия — ходить может только он.',
    targetHint: 'Сходите бием на подсвеченную клетку: можно взять или просто передвинуться.',
    textKey: 'tutorial.section3.step3.text',
  },
  3: {
    blackCells: [10, 29, 41],
    pieces: {
      37: { piece: 'белый бий', captures: { 21: 29 } },
      35: { piece: 'белая шатра', captures: { 23: 29, 47: 41 } },
      13: { piece: 'белый батыр', captures: { 9: 10, 48: 41 } },
    },
    selectHint: 'Взять могут бий, шатра или батыр — выберите любую из них.',
    targetHint: 'Кликните на подсвеченную клетку приземления для взятия.',
    textKey: 'tutorial.section3.step4.text',
  },
};

export default function TutorialSection3() {
  return <CaptureLesson steps={STEPS} lastStepIndex={3} />;
}
