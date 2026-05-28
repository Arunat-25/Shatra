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
  onDeclineDraw,
  onResign,
  drawPending = false,
  drawIncoming = false,
}) {
  const drawActive = drawPending || drawIncoming;

  let drawTitle = 'Предложить ничью';
  if (drawPending) drawTitle = 'Ожидание ответа соперника';
  else if (drawIncoming) drawTitle = 'Принять ничью';

  return (
    <div className="room-actions-block">
      {canPass && (
        <button type="button" className="btn-sidebar" onClick={onPass}>
          Передать
        </button>
      )}
      <div className="room-icon-actions">
        <button
          type="button"
          className={[
            'room-icon-btn',
            drawActive ? 'room-icon-btn--draw-active' : '',
          ].filter(Boolean).join(' ')}
          onClick={onOfferDraw}
          disabled={drawPending}
          title={drawTitle}
          aria-label={drawTitle}
        >
          <span className="room-icon-half">½</span>
        </button>
        {drawIncoming && (
          <button
            type="button"
            className="room-icon-btn room-icon-btn--draw-active room-icon-btn--draw-decline"
            onClick={onDeclineDraw}
            title="Отклонить ничью"
            aria-label="Отклонить ничью"
          >
            <span className="room-icon-decline">✕</span>
          </button>
        )}
        <button
          type="button"
          className="room-icon-btn room-icon-btn--danger"
          onClick={onResign}
          title="Сдаться"
          aria-label="Сдаться"
        >
          <FlagIcon />
        </button>
      </div>
    </div>
  );
}
