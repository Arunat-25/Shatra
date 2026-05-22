import { useRef } from 'react';

import PropTypes from 'prop-types';

export default function GameInfo({ whiteCount, blackCount, roomId, modeAi, canPass, gameOver, onSkipTurn, onCopyLink, myColor }) {
  const linkInputRef = useRef(null);

  const handleCopyLink = () => {
    if (linkInputRef.current) {
      const playerSuffix = myColor === 'черный' ? '&player=2' : '';
      linkInputRef.current.value = `${window.location.origin}/game?room=${roomId}${playerSuffix}`;
      linkInputRef.current.select();
      navigator.clipboard.writeText(linkInputRef.current.value);
      onCopyLink?.();
    }
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
      <input
        ref={linkInputRef}
        type="text"
        readOnly
        style={{ position: 'absolute', opacity: 0, pointerEvents: 'none', height: 0, width: 0 }}
        value=""
      />
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
  myColor: PropTypes.string,
};
