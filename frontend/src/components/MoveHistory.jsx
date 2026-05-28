import { useEffect, useRef } from 'react';

const COLOR_LABELS = { 'белый': 'Белые', 'черный': 'Чёрные' };

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
  const listRef = useRef(null);

  // Прокрутка вниз только при новом ходе в live-режиме (не мешает листать вверх).
  useEffect(() => {
    if (viewingHistoryIndex !== null) return;
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [movesHistory.length, viewingHistoryIndex]);

  return (
    <div className="move-history-panel">
      <div className="move-history-header">
        <span>История ходов</span>
        {movesHistory.length > 0 && (
          <span className="move-history-count">{movesHistory.length} ход.</span>
        )}
      </div>

      <div className="move-history-list" ref={listRef}>
        {movesHistory.length === 0 ? (
          <div className="move-history-empty">Ходов пока нет</div>
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
              >
                <span className="move-number">{entry.move_number}.</span>
                <span className="move-color">{COLOR_LABELS[entry.mover] || entry.mover}</span>
                <span className="move-from-to">{entry.from_pos} → {entry.to_pos}</span>
              </div>
            );
          })
        )}
      </div>

      <div className="move-history-nav">
        <button
          className="move-history-nav-btn"
          onClick={onStepBack}
          disabled={!canStepBack}
          aria-label="Ход назад"
          title="Ход назад"
        >
          ←
        </button>
        <span className="move-history-page" title="Позиция в истории">
          {movesHistory.length === 0
            ? '0/0'
            : (viewingHistoryIndex === null ? `${movesHistory.length}/${movesHistory.length}` : `${viewingHistoryIndex + 1}/${movesHistory.length}`)}
        </span>
        <button
          className="move-history-nav-btn"
          onClick={onStepForward}
          disabled={!canStepForward}
          aria-label="Ход вперёд"
          title="Ход вперёд"
        >
          →
        </button>
      </div>

      {viewingHistoryIndex !== null && (
        <button className="move-history-back-btn" onClick={onExitHistory}>
          ← Вернуться к игре
        </button>
      )}
    </div>
  );
}
