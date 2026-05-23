import PropTypes from 'prop-types';

export default function GameInfo({ whiteCount, blackCount, roomId, modeAi, canPass, gameOver, onSkipTurn, onCopyLink }) {
  const handleCopyLink = () => {
    const link = `${window.location.origin}/${roomId}`;
    navigator.clipboard.writeText(link).then(onCopyLink).catch(() => {});
  };

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
        <span>
          Комната: <span className="room-link" onClick={handleCopyLink}>{roomId}</span>
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
  roomId: PropTypes.string,
  modeAi: PropTypes.bool,
  canPass: PropTypes.bool,
  gameOver: PropTypes.bool,
  onSkipTurn: PropTypes.func.isRequired,
  onCopyLink: PropTypes.func.isRequired,
};
