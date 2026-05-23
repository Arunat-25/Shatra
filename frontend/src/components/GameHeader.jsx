import PropTypes from 'prop-types';

export default function GameHeader({ myColor, moversColor, aiThinking, modeAi, onGoToLobby, timer, timeControl, playerId }) {
  const formatTime = (seconds) => {
    if (seconds === null || seconds === undefined) return null;
    const s = Math.max(0, Math.round(seconds));
    const mins = Math.floor(s / 60);
    const secs = s % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const whiteTime = timer ? formatTime(timer['белый']) : null;
  const blackTime = timer ? formatTime(timer['черный']) : null;

  const whiteLow = timer && timer['белый'] <= 15;
  const blackLow = timer && timer['черный'] <= 15;

  return (
    <div className="game-header">
      <div className="header-left">
        <span className="game-title" onClick={onGoToLobby} title="Вернуться в лобби">Шатра</span>
        <div className="player-info">
          <span className={`player-badge ${myColor === 'белый' ? 'color-white' : 'color-black'}`}>
            {myColor === 'белый' ? '⚪' : '⚫'} {myColor === 'белый' ? 'Белые' : 'Черные'}
            {playerId && <span className="player-id" title={playerId}> #{playerId.slice(0, 6)}</span>}
          </span>
          {modeAi && <span className="ai-badge">AI</span>}
        </div>
      </div>
      <div className="header-right">
        {timeControl && (
          <div className="timer-display">
            <span className={`timer-item ${moversColor === 'белый' ? 'timer-active' : ''} ${whiteLow ? 'timer-low' : ''}`}>
              ⚪ {whiteTime}
            </span>
            <span className="timer-separator">|</span>
            <span className={`timer-item ${moversColor === 'черный' ? 'timer-active' : ''} ${blackLow ? 'timer-low' : ''}`}>
              ⚫ {blackTime}
            </span>
          </div>
        )}
        <div className={`turn-indicator ${moversColor === 'белый' ? 'turn-white' : 'turn-black'} ${aiThinking ? 'turn-ai' : ''} ${!aiThinking && moversColor === myColor ? 'turn-your-turn' : ''}`}>
          {aiThinking ? (
            <span className="ai-thinking-text">
              AI думает
              <span className="thinking-dot">.</span>
              <span className="thinking-dot">.</span>
              <span className="thinking-dot">.</span>
            </span>
          ) : (
            <>Ход: {moversColor === 'белый' ? '⚪' : '⚫'} {moversColor === 'белый' ? 'Белых' : 'Черных'}</>
          )}
        </div>
        <button className="btn-exit" onClick={onGoToLobby} title="Выйти в лобби">
          ✕
        </button>
      </div>
    </div>
  );
}

GameHeader.propTypes = {
  myColor: PropTypes.string,
  moversColor: PropTypes.string,
  aiThinking: PropTypes.bool,
  modeAi: PropTypes.bool,
  onGoToLobby: PropTypes.func.isRequired,
  timer: PropTypes.shape({
    белый: PropTypes.number,
    черный: PropTypes.number,
  }),
  timeControl: PropTypes.number,
  playerId: PropTypes.string,
};
