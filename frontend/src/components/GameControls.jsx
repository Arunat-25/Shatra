import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';

const RESIGN_ARM_MS = 4000;

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
  onResign,
  drawPending = false,
  drawIncoming = false,
  canCancelGame = false,
  hideDraw = false,
}) {
  const { t } = useTranslation();
  const [resignArmed, setResignArmed] = useState(false);

  useEffect(() => {
    if (!resignArmed) return undefined;
    const timer = setTimeout(() => setResignArmed(false), RESIGN_ARM_MS);
    return () => clearTimeout(timer);
  }, [resignArmed]);

  const handleResignClick = useCallback(() => {
    if (!resignArmed) {
      setResignArmed(true);
      return;
    }
    setResignArmed(false);
    onResign();
  }, [resignArmed, onResign]);

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
            'room-icon-btn--danger',
            resignArmed ? 'room-icon-btn--resign-armed' : '',
          ].filter(Boolean).join(' ')}
          onClick={handleResignClick}
          title={resignArmed ? t('controls.resignConfirm') : t('controls.resign')}
          aria-label={resignArmed ? t('controls.resignConfirmAria') : t('controls.resign')}
        >
          <FlagIcon />
        </button>
      </div>
    </div>
  );
}
