import PropTypes from 'prop-types';

export default function GameHeader({ moversColor, aiThinking, onGoToLobby }) {
  return (
    <div className="game-header">
      <div className="header-left">
        <span className="game-title" onClick={onGoToLobby} title="Вернуться в лобби">Шатра</span>
      </div>
      <div className="header-right">
        <div
          className={[
            'turn-indicator',
            moversColor === 'белый' ? 'turn-white' : 'turn-black',
            aiThinking ? 'turn-ai' : '',
          ].filter(Boolean).join(' ')}
          title={aiThinking ? 'AI думает' : 'Чей ход'}
        >
          {aiThinking ? '…' : (moversColor === 'белый' ? '⚪' : '⚫')}
        </div>
      </div>
    </div>
  );
}

GameHeader.propTypes = {
  moversColor: PropTypes.string,
  aiThinking: PropTypes.bool,
  onGoToLobby: PropTypes.func.isRequired,
};
