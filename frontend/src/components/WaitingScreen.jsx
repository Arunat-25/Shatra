import { useCallback, useMemo } from 'react';

function CopyIcon() {
  return (
    <svg className="waiting-copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

export default function WaitingScreen({
  roomId,
  modeAi,
  showInviteLink = false,
  joiningError,
  reconnectMessage,
}) {
  const inviteUrl = useMemo(
    () => (roomId ? `${window.location.origin}/${roomId}` : ''),
    [roomId],
  );

  const copyLink = useCallback(() => {
    if (!inviteUrl) return;
    navigator.clipboard.writeText(inviteUrl);
  }, [inviteUrl]);

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
      <div className={`waiting-content ${showInviteLink ? 'waiting-content--invite' : ''}`}>
        {joiningError ? (
          <div className="waiting-error">
            <div className="waiting-error-icon">⚠️</div>
            <h2 className="waiting-title" style={{ color: 'var(--color-accent)' }}>Ошибка</h2>
            <div className="error-container">
              <p>{joiningError}</p>
            </div>
          </div>
        ) : showInviteLink ? (
          <>
            <h1 className="waiting-invite-heading">Вызов другу</h1>
            <div className="waiting-link-row">
              <p className="waiting-link-url">{inviteUrl}</p>
              <button
                type="button"
                className="btn-copy-icon"
                onClick={copyLink}
                title="Копировать ссылку"
                aria-label="Копировать ссылку"
              >
                <CopyIcon />
              </button>
            </div>
            <p className="waiting-invite-note">
              С вами сыграет первый, кто перейдёт по ссылке
            </p>
            {reconnectMessage && <p className="waiting-hint">{reconnectMessage}</p>}
          </>
        ) : (
          <>
            <div className="waiting-spinner" />
            <h2 className="waiting-title">Ожидание соперника</h2>
            <p className="waiting-subtitle">Комната в зале ожидания</p>
            <p className="waiting-hint">Игра начнётся, когда кто-то присоединится из списка</p>
            {reconnectMessage && <p className="waiting-hint">{reconnectMessage}</p>}
          </>
        )}
      </div>
    </div>
  );
}
