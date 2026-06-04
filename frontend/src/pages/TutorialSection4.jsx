import CaptureLesson from '../components/tutorial/CaptureLesson';

const STEPS = {
  0: {
    blackCells: [41, 42, 35, 53, 37],
    chains: {
      27: [
        { piecePos: 27, piece: 'белая шатра', captures: { 43: 35 } },
        { piecePos: 43, piece: 'белая шатра', captures: { 31: 37 } },
      ],
      56: [
        { piecePos: 56, piece: 'белая шатра', captures: { 48: 53 } },
        {
          piecePos: 48,
          piece: 'белая шатра',
          captures: { 34: 41, 36: 42 },
          branches: {
            34: {
              piecePos: 34,
              piece: 'белая шатра',
              captures: { 36: 35 },
              branches: {
                36: {
                  piecePos: 36,
                  piece: 'белая шатра',
                  captures: { 48: 42, 38: 37 },
                  branches: {
                    48: { complete: true },
                    38: { complete: true },
                  },
                },
              },
            },
            36: {
              piecePos: 36,
              piece: 'белая шатра',
              captures: { 34: 35, 38: 37 },
              branches: {
                34: { piecePos: 34, piece: 'белая шатра', captures: { 48: 41 } },
                38: { complete: true },
              },
            },
          },
        },
      ],
    },
    selectHint: 'Кликните на белую шатру — нужно сделать серию взятий.',
    targetHint: 'Сделайте взятие на подсвеченную клетку.',
    chainContinueHint: 'Та же шатра обязана продолжить взятие — сходите ещё раз.',
    textKey: 'tutorial.section4.step1.text',
  },
  1: {
    blackCells: [14, 21, 22, 23, 27, 29, 17],
    blackPieces: { 16: 'черный бий' },
    chain: [
      {
        piecePos: 48,
        piece: 'белый батыр',
        captures: { 13: 27, 20: 27 },
        branches: {
          13: {
            piecePos: 13,
            piece: 'белый батыр',
            captures: { 15: 14 },
            branches: {
              15: {
                piecePos: 15,
                piece: 'белый батыр',
                captures: { 31: 23 },
                branches: {
                  31: {
                    piecePos: 31,
                    piece: 'белый батыр',
                    captures: { 28: 29 },
                    branches: {
                      28: { complete: true },
                    },
                  },
                },
              },
            },
          },
          20: { complete: true },
        },
      },
    ],
    selectHint: 'Кликните на белого батыра — нужно сделать серию взятий.',
    targetHint: 'Сделайте взятие на подсвеченную клетку.',
    chainContinueHint: 'Тот же батыр обязан продолжить взятие — сходите ещё раз.',
    textKey: 'tutorial.section4.step2.text',
  },
  2: {
    blackCells: [12, 14, 18],
    blackPieces: { 15: 'черный бий', 32: 'черная шатра' },
    allowPassTurn: true,
    chain: [
      { piecePos: 39, piece: 'белый бий', captures: { 25: 32 } },
      { piecePos: 25, piece: 'белый бий', captures: { 11: 18 } },
      { piecePos: 11, piece: 'белый бий', captures: { 13: 12 } },
    ],
    selectHint: 'Кликните на белого бия — можно взять несколько раз подряд.',
    targetHint: 'Сделайте взятие на подсвеченную клетку.',
    chainContinueHint:
      'Бий может продолжить взятие — сходите ещё раз или передайте ход, если взятия достаточно.',
    textKey: 'tutorial.section4.step3.text',
  },
};

export default function TutorialSection4() {
  return <CaptureLesson steps={STEPS} lastStepIndex={2} />;
}
