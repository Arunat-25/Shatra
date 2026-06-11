import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PlayerNick from './PlayerNick';
import { playerNickname, playerRating } from '../utils/playerDisplay';

function CopyIcon() {
  return (
    <svg className="waiting-copy-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

async function copyTextToClipboard(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // fallback below
    }
  }
  try {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.left = '-9999px';
    document.body.appendChild(textarea);
    textarea.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(textarea);
    return ok;
  } catch {
    return false;
  }
}

export default function WaitingScreen({
  roomId,
  modeAi,
  showInviteLink = false,
  joiningError,
  reconnectMessage,
  opponent,
  onCopyFeedback,
}) {
  const { t } = useTranslation();
  const opponentRating = opponent ? playerRating(opponent) : null;
  const [copyStatus, setCopyStatus] = useState('');
  const [qrDataUrl, setQrDataUrl] = useState('');

  const inviteUrl = useMemo(
    () => (roomId ? `${window.location.origin}/${roomId}` : ''),
    [roomId],
  );

  useEffect(() => {
    if (!showInviteLink || !inviteUrl) {
      setQrDataUrl('');
      return undefined;
    }
    let cancelled = false;
    import('qrcode')
      .then(({ default: QRCode }) => QRCode.toDataURL(inviteUrl, { width: 120, margin: 1 }))
      .then((url) => {
        if (!cancelled) setQrDataUrl(url);
      })
      .catch(() => {
        if (!cancelled) setQrDataUrl('');
      });
    return () => { cancelled = true; };
  }, [showInviteLink, inviteUrl]);

  const copyLink = useCallback(async () => {
    if (!inviteUrl) return;
    const ok = await copyTextToClipboard(inviteUrl);
    const message = ok ? t('game.linkCopied') : t('game.linkCopyFailed');
    setCopyStatus(message);
    onCopyFeedback?.(ok ? 'success' : 'error', message);
    if (ok) {
      setTimeout(() => setCopyStatus(''), 2500);
    }
  }, [inviteUrl, onCopyFeedback, t]);

  if (modeAi) {
    return (
      <div className="waiting-screen">
        <div className="waiting-content">
          <div className="waiting-spinner" />
          <h2 className="waiting-title">{t('game.aiTitle')}</h2>
          <p className="waiting-subtitle">{t('game.aiConnecting')}</p>
          <p className="waiting-hint">{t('game.boardSoon')}</p>
          {reconnectMessage && <p className="waiting-hint">{reconnectMessage}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className={`waiting-screen ${showInviteLink ? 'waiting-screen--invite' : ''}`}>
      <div className={`waiting-content ${showInviteLink ? 'waiting-content--invite' : ''}`}>
        {joiningError ? (
          <div className="waiting-error">
            <div className="waiting-error-icon">⚠️</div>
            <h2 className="waiting-title" style={{ color: 'var(--color-accent)' }}>{t('game.error')}</h2>
            <div className="error-container">
              <p>{joiningError}</p>
            </div>
          </div>
        ) : showInviteLink ? (
          <>
            <h1 className="waiting-invite-heading">{t('game.inviteHeading')}</h1>
            <div className="waiting-invite-share">
              {qrDataUrl && (
                <img
                  className="waiting-qr"
                  src={qrDataUrl}
                  width={120}
                  height={120}
                  alt={t('game.qrLabel')}
                />
              )}
              <div className="waiting-invite-link-block">
                <div className="waiting-link-row">
                  <p className="waiting-link-url">{inviteUrl}</p>
                  <button
                    type="button"
                    className="btn-copy-icon"
                    onClick={copyLink}
                    title={t('game.copyLink')}
                    aria-label={t('game.copyLink')}
                  >
                    <CopyIcon />
                  </button>
                </div>
                {copyStatus && <p className="waiting-copy-status">{copyStatus}</p>}
              </div>
            </div>
            <p className="waiting-invite-note">
              {t('game.inviteNote')}
            </p>
            {reconnectMessage && <p className="waiting-hint">{reconnectMessage}</p>}
          </>
        ) : (
          <>
            <div className="waiting-spinner" />
            <h2 className="waiting-title">{t('game.waitingOpponent')}</h2>
            <p className="waiting-subtitle">{t('game.waitingLobby')}</p>
            <p className="waiting-hint">{t('game.waitingHint')}</p>
            {opponent && (
              <p className="waiting-hint waiting-opponent">
                {t('game.opponent')}:{' '}
                <PlayerNick
                  nickname={playerNickname(opponent, opponent.color, t)}
                  rating={opponentRating}
                  showRating={opponentRating != null}
                  className="waiting-opponent-nick"
                />
              </p>
            )}
            {reconnectMessage && <p className="waiting-hint">{reconnectMessage}</p>}
          </>
        )}
      </div>
    </div>
  );
}
