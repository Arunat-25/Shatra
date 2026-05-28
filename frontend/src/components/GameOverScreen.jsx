import { useNavigate } from 'react-router-dom';
import { isWinner } from '../utils';

export default function GameOverScreen({ winner, myColor, modeAi, reason, onGoToLobby, onViewHistory }) {
  const navigate = useNavigate();
  const isWin = isWinner(winner, myColor);
  const isDisconnect = reason === 'opponent_disconnected';

  return (
    <div className="game-over-overlay">
      <div className="game-over-modal">
        <div className="game-over-icon">{isWin ? '🏆' : '😔'}</div>
        <h2 className="game-over-title">{isWin ? 'Победа!' : 'Поражение'}</h2>
        <p className="game-over-text">
          {isDisconnect
            ? 'Соперник покинул игру. Ваша победа!'
            : winner
              ? (isWin ? 'Вы одержали победу!' : `Победил ${winner}`)
              : 'Ничья'}
        </p>
        <div className="game-over-buttons">
          {onViewHistory && (
            <button type="button" className="btn-secondary btn-history" onClick={onViewHistory}>
              Просмотреть историю
            </button>
          )}
          <button className="btn-lobby btn-battle" onClick={onGoToLobby}>
            В лобби
          </button>
          {modeAi && (
            <button className="btn-lobby btn-ai" onClick={() => navigate(0)}>
              Играть снова
            </button>
          )}
        </div>
      </div>
    </div>
  );
}