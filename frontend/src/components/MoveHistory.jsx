import { useRef, useEffect } from 'react';

const COLOR_LABELS = { 'белый': 'Белые', 'черный': 'Чёрные' };

export default function MoveHistory({
  movesHistory,
  viewingHistoryIndex,
  onViewMove,
  onExitHistory,
}) {
  const listRef = useRef(null);

  // Автоскролл к последнему ходу
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [movesHistory.length]);

  return (
    <div className="move-history-panel">
      <div className="move-history-header">История ходов</div>
      <div className="move-history-list" ref={listRef}>
        {movesHistory.length === 0 && (
          <div className="move-history-empty">Ходов пока нет</div>
        )}
        {movesHistory.map((entry, idx) => (
          <div
            key={idx}
            className={`move-history-item ${idx === viewingHistoryIndex ? 'move-history-item--active' : ''} ${idx === movesHistory.length - 1 && viewingHistoryIndex === null ? 'move-history-item--latest' : ''}`}
            onClick={() => onViewMove(idx)}
          >
            <span className="move-number">{entry.move_number}.</span>
            <span className="move-color">{COLOR_LABELS[entry.mover] || entry.mover}</span>
            <span className="move-from-to">{entry.from_pos} → {entry.to_pos}</span>
          </div>
        ))}
      </div>
      {viewingHistoryIndex !== null && (
        <button className="move-history-back-btn" onClick={onExitHistory}>
          ← Вернуться к игре
        </button>
      )}
    </div>
  );
}