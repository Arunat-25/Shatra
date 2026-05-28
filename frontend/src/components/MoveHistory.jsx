import { useState, useEffect } from 'react';

const COLOR_LABELS = { 'белый': 'Белые', 'черный': 'Чёрные' };
const PAGE_SIZE = 5;

export default function MoveHistory({
  movesHistory,
  viewingHistoryIndex,
  onViewMove,
  onExitHistory,
}) {
  const totalPages = Math.max(1, Math.ceil(movesHistory.length / PAGE_SIZE));
  const [page, setPage] = useState(0);

  useEffect(() => {
    setPage(Math.max(0, Math.ceil(movesHistory.length / PAGE_SIZE) - 1));
  }, [movesHistory.length]);

  const start = page * PAGE_SIZE;
  const visibleMoves = movesHistory.slice(start, start + PAGE_SIZE);

  return (
    <div className="move-history-panel">
      <div className="move-history-header">
        <span>История ходов</span>
        {movesHistory.length > 0 && (
          <span className="move-history-count">{movesHistory.length} ход.</span>
        )}
      </div>

      <div className="move-history-list">
        {movesHistory.length === 0 ? (
          <div className="move-history-empty">Ходов пока нет</div>
        ) : (
          visibleMoves.map((entry, i) => {
            const idx = start + i;
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
          onClick={() => setPage(p => Math.max(0, p - 1))}
          disabled={page === 0}
          aria-label="Предыдущие ходы"
          title="Предыдущие ходы"
        >
          ←
        </button>
        <span className="move-history-page">
          {page + 1} / {totalPages}
        </span>
        <button
          className="move-history-nav-btn"
          onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
          disabled={page >= totalPages - 1}
          aria-label="Следующие ходы"
          title="Следующие ходы"
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
