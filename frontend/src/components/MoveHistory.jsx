import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { COLOR_BLACK, COLOR_WHITE } from '../constants';

export default function MoveHistory({
  movesHistory,
  viewingHistoryIndex,
  onViewMove,
  onExitHistory,
  onStepBack,
  onStepForward,
  canStepBack,
  canStepForward,
}) {
  const { t } = useTranslation();
  const listRef = useRef(null);

  const moverAbbr = {
    [COLOR_WHITE]: t('colors.whiteAbbr'),
    [COLOR_BLACK]: t('colors.blackAbbr'),
  };

  const formatMoveLabel = (entry) => {
    const side = moverAbbr[entry.mover] || '?';
    return `${entry.move_number}. ${side} ${entry.from_pos}-${entry.to_pos}`;
  };

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    if (viewingHistoryIndex !== null) {
      const active = el.querySelector('.move-history-item--active');
      active?.scrollIntoView({ inline: 'nearest', block: 'nearest', behavior: 'smooth' });
      return;
    }
    el.scrollTop = el.scrollHeight;
    el.scrollLeft = el.scrollWidth;
  }, [movesHistory.length, viewingHistoryIndex]);

  return (
    <div className="move-history-panel">
      <div className="move-history-header">
        <span className="move-history-title">{t('history.title')}</span>
        {movesHistory.length > 0 && (
          <span className="move-history-count">{t('history.movesCount', { count: movesHistory.length })}</span>
        )}
      </div>

      <div className="move-history-strip">
        <button
          type="button"
          className="move-history-nav-btn move-history-nav-btn--prev move-history-nav-btn--strip"
          onClick={onStepBack}
          disabled={!canStepBack}
          aria-label={t('history.stepBack')}
          title={t('history.stepBack')}
        >
          ←
        </button>

        <div className="move-history-list" ref={listRef}>
          {movesHistory.length === 0 ? (
            <div className="move-history-empty">{t('history.empty')}</div>
          ) : (
            movesHistory.map((entry, idx) => {
              const isActive = idx === viewingHistoryIndex;
              const isLatest = idx === movesHistory.length - 1 && viewingHistoryIndex === null;
              return (
                <div
                  key={idx}
                  className={[
                    'move-history-item',
                    isActive ? 'move-history-item--active' : '',
                    isLatest ? 'move-history-item--latest' : '',
                  ].filter(Boolean).join(' ')}
                  onClick={() => onViewMove(idx)}
                  title={`${entry.mover}: ${entry.from_pos} → ${entry.to_pos}`}
                >
                  <span className="move-history-line">{formatMoveLabel(entry)}</span>
                </div>
              );
            })
          )}
        </div>

        <button
          type="button"
          className="move-history-nav-btn move-history-nav-btn--next move-history-nav-btn--strip"
          onClick={onStepForward}
          disabled={!canStepForward}
          aria-label={t('history.stepForward')}
          title={t('history.stepForward')}
        >
          →
        </button>
      </div>

      <div className="move-history-nav move-history-nav--desktop">
        <button
          type="button"
          className="move-history-nav-btn"
          onClick={onStepBack}
          disabled={!canStepBack}
          aria-label={t('history.stepBack')}
          title={t('history.stepBack')}
        >
          ←
        </button>
        <span className="move-history-page" title={t('history.position')}>
          {movesHistory.length === 0
            ? '0/0'
            : (viewingHistoryIndex === null ? `${movesHistory.length}/${movesHistory.length}` : `${viewingHistoryIndex + 1}/${movesHistory.length}`)}
        </span>
        <button
          type="button"
          className="move-history-nav-btn"
          onClick={onStepForward}
          disabled={!canStepForward}
          aria-label={t('history.stepForward')}
          title={t('history.stepForward')}
        >
          →
        </button>
      </div>

      {viewingHistoryIndex !== null && (
        <button className="move-history-back-btn" onClick={onExitHistory}>
          {t('history.backToGame')}
        </button>
      )}
    </div>
  );
}
