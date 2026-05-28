export default function RoomCard({ room, isJoining, onJoin }) {
  const { room_id, type, created_at } = room;
  const roomInfo = getRoomInfo(type);

  return (
    <div
      className={`room-card ${isJoining ? 'room-card-joining' : ''}`}
      onClick={() => !isJoining && onJoin(room_id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && !isJoining) {
          e.preventDefault();
          onJoin(room_id);
        }
      }}
    >
      <div className="room-card-left">
        <span className="room-card-type">
          <span className={`room-card-type-badge ${roomInfo.badge}`} title={roomInfo.label}>
            {roomInfo.icon}
          </span>
          {roomInfo.label}
        </span>
        <span className="room-card-id">{room_id}</span>
      </div>
      <div className="room-card-right">
        <span className="room-card-time">
          {new Date(created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
        <button
          type="button"
          className="btn-join"
          disabled={isJoining}
          onClick={(e) => { e.stopPropagation(); if (!isJoining) onJoin(room_id); }}
        >
          {isJoining ? '…' : 'Войти'}
        </button>
      </div>
    </div>
  );
}

const ROOM_LABELS = {
  quick: {
    label: 'Быстрая игра',
    badge: 'quick',
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    ),
  },
  friend: {
    label: 'Вызов другу',
    badge: 'friend',
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  ai: {
    label: 'Игра с ботом',
    badge: 'ai',
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
        <rect x="5" y="9" width="14" height="10" rx="2" />
        <path d="M9 9V7a3 3 0 0 1 6 0v2" />
      </svg>
    ),
  },
};
const DEFAULT_ROOM = ROOM_LABELS.quick;

function getRoomInfo(type) {
  return ROOM_LABELS[type] || DEFAULT_ROOM;
}
