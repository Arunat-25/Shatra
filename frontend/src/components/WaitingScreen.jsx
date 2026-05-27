import { useRef } from 'react';

export default function WaitingScreen({ roomId, modeAi, joiningError, reconnectMessage }) {
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
          <p className="waiting-subtitle">Подключение к игре…</p>
          <p className="waiting-hint">Скоро откроется доска</p>
          {reconnectMessage && <p className="waiting-hint">{reconnectMessage}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="waiting-screen">
      <div className="waiting-content">
        {joiningError ? (
          <div className="waiting-error">
            <div className="waiting-error-icon">⚠️</div>
            <h2 className="waiting-title" style={{ color: 'var(--color-accent)' }}>Ошибка</h2>
            <div className="error-container">
              <p>{joiningError}</p>
            </div>
          </div>
        ) : (
          <>
            <div className="waiting-spinner" />
            <h2 className="waiting-title">Ожидание соперника</h2>
            <p className="waiting-subtitle">Поделитесь ссылкой, чтобы пригласить друга</p>
            <div className="waiting-link-container">
              <input
                className="waiting-link-input"
                ref={linkInputRef}
                type="text"
                readOnly
                value={`${window.location.origin}/${roomId}`}
                onClick={() => linkInputRef.current?.select()}
              />
              <button className="btn-refresh" onClick={copyLink}>Копировать</button>
            </div>
            <p className="waiting-hint">Игра начнётся, когда второй игрок присоединится</p>
            {reconnectMessage && <p className="waiting-hint">{reconnectMessage}</p>}
          </>
        )}
      </div>
    </div>
  );
}
