import PropTypes from 'prop-types';

export default function GameInfo({ whiteCount, blackCount, modeAi, canPass, gameOver, onSkipTurn }) {
  return (
    <>
      {canPass && !gameOver && (
        <button className="btn-pass" onClick={onSkipTurn}>Передать ход</button>
      )}

      <div className="game-info-bottom">
        <span className="piece-count">
          <span className="piece-count-item">⚪ {whiteCount}</span>
          <span className="piece-count-item">⚫ {blackCount}</span>
        </span>
        {modeAi && <span className="game-info-ai">🤖 AI</span>}
      </div>
      <div className="keyboard-hint">
        <span className="kbd">Esc</span> — отменить выбор фигуры
      </div>
    </>
  );
}

GameInfo.propTypes = {
  whiteCount: PropTypes.number.isRequired,
  blackCount: PropTypes.number.isRequired,
  modeAi: PropTypes.bool,
  canPass: PropTypes.bool,
  gameOver: PropTypes.bool,
  onSkipTurn: PropTypes.func.isRequired,
};
