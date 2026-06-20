import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { isSoundEnabled, setSoundEnabled } from '../audio/soundSettings';
import { resumeAudioContext, preloadGameSounds } from '../audio/gameSounds';

function SoundIcon({ muted }) {
  return (
    <svg className="room-icon-svg" viewBox="0 0 24 24" aria-hidden="true">
      {muted ? (
        <>
          <path
            d="M11 5L6 9H3v6h3l5 4V5z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="M16 9l5 6M21 9l-5 6"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </>
      ) : (
        <>
          <path
            d="M11 5L6 9H3v6h3l5 4V5z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="M15.5 8.5a4.5 4.5 0 010 7M18 6a7.5 7.5 0 010 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </>
      )}
    </svg>
  );
}

function FlagIcon() {
  return (
    <svg className="room-icon-svg" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M5 3v18M5 4h9.5c1.2 0 2.3-.6 3-1.5.7.9 1.8 1.5 3 1.5H21v11h-2.5c-1.2 0-2.3.6-3 1.5-.7-.9-1.8-1.5-3-1.5H5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function GameControls({
  canPass,
  onPass,
  onOfferDraw,
  onAcceptDraw,
  onDeclineDraw,
  onCancelGame,
  onResignClick,
  resignArmed = false,
  drawPending = false,
  drawIncoming = false,
  canCancelGame = false,
  hideDraw = false,
}) {
  const { t } = useTranslation();
  const [soundOn, setSoundOn] = useState(() => isSoundEnabled());

  const toggleSound = useCallback(async () => {
    await resumeAudioContext();
    await preloadGameSounds();
    const next = !soundOn;
    setSoundOn(next);
    setSoundEnabled(next);
  }, [soundOn]);

  return (
    <div className="room-actions-block">
      {canPass && (
        <button type="button" className="btn-sidebar" onClick={onPass}>
          {t('controls.pass')}
        </button>
      )}
      <div className="room-icon-actions">
        {!hideDraw && (
          drawIncoming ? (
            <>
              <button
                type="button"
                className="btn-draw-text btn-draw-text--accept room-icon-btn--draw-active"
                onClick={onAcceptDraw}
                title={t('controls.acceptDraw')}
              >
                {t('controls.acceptDraw')}
              </button>
              <button
                type="button"
                className="room-icon-btn room-icon-btn--draw-active room-icon-btn--draw-decline"
                onClick={onDeclineDraw}
                title={t('controls.declineDraw')}
                aria-label={t('controls.declineDraw')}
              >
                <span className="room-icon-decline">✕</span>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className={[
                  'room-icon-btn',
                  drawPending ? 'room-icon-btn--draw-active' : '',
                ].filter(Boolean).join(' ')}
                onClick={onOfferDraw}
                disabled={drawPending}
                title={drawPending ? t('controls.drawPending') : t('controls.offerDraw')}
                aria-label={drawPending ? t('controls.drawPending') : t('controls.offerDraw')}
              >
                <span className="room-icon-half">½</span>
              </button>
              {canCancelGame && (
                <button
                  type="button"
                  className="room-icon-btn room-icon-btn--cancel"
                  onClick={onCancelGame}
                  title={t('controls.cancelGame')}
                  aria-label={t('controls.cancelGame')}
                >
                  <span className="room-icon-decline">✕</span>
                </button>
              )}
            </>
          )
        )}
        <button
          type="button"
          className={[
            'room-icon-btn',
            soundOn ? '' : 'room-icon-btn--sound-off',
          ].filter(Boolean).join(' ')}
          onClick={toggleSound}
          title={soundOn ? t('game.sounds.on') : t('game.sounds.off')}
          aria-label={soundOn ? t('game.sounds.on') : t('game.sounds.off')}
          aria-pressed={soundOn}
        >
          <SoundIcon muted={!soundOn} />
        </button>
        <button
          type="button"
          className={[
            'room-icon-btn',
            'room-icon-btn--danger',
            resignArmed ? 'room-icon-btn--resign-armed' : '',
          ].filter(Boolean).join(' ')}
          onClick={onResignClick}
          title={resignArmed ? t('controls.resignConfirm') : t('controls.resign')}
          aria-label={resignArmed ? t('controls.resignConfirmAria') : t('controls.resign')}
        >
          <FlagIcon />
        </button>
      </div>
    </div>
  );
}
