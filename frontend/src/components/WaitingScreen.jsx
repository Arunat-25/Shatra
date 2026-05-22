import { useRef } from 'react';

export default function WaitingScreen({ roomId, playerId, modeFriend, modeAi, joiningError }) {
  const linkInputRef = useRef(null);

  const copyLink = () => {
    if (linkInputRef.current) {
      linkInputRef.current.select();
      navigator.clipboard.writeText(linkInputRef.current.value);
    }
  };

  if (modeAi) {
    return (
      <div className="waiting-screen">
        <div className="waiting-content">
          <div className="waiting-spinner" />
          <h2 className="waiting-title">Сражение с ботом</h2>
          <p className="waiting-subtitle">🤖 ИИ анализирует позицию...</p>
          <p className="waiting-hint">Игра начнётся, когда бот будет готов</p>
        </div>
      </div>
    );
  }

  return (
    <div className="waiting-screen">
      <div className="waiting-content">
        <div className="waiting-spinner" />
        <h2 className="waiting-title">Ожидание соперника</h2>
        {(playerId === null || modeFriend) && (
          <>
            <p className="waiting-subtitle">Поделитесь ссылкой, чтобы пригласить друга</p>
            <div className="waiting-link-container">
              <input
                className="waiting-link-input"
                ref={linkInputRef}
                type="text"
                readOnly
                value={`${window.location.origin}/game?room=${roomId}`}
                onClick={() => linkInputRef.current?.select()}
              />
              <button className="btn-refresh" onClick={copyLink}>Копировать</button>
            </div>
          </>
        )}
        <p className="waiting-hint">Игра начнётся, когда второй игрок присоединится</p>
        {joiningError && (
          <div className="error-container">
            <p>{joiningError}</p>
          </div>
        )}
      </div>
    </div>
  );
}