export default function RoomCard({ room, isJoining, onJoin }) {
  const { room_id, type, created_at } = room;
  const roomInfo = getRoomInfo(type);

  return (
    <div
      className={`room-card ${isJoining ? 'room-card-joining' : ''}`}
      onClick={() => !isJoining && onJoin(room_id)}
    >
      <div className="room-card-left">
        <span className="room-card-type">
          <span className={`room-card-type-badge ${roomInfo.badge}`}>{roomInfo.icon}</span>
          {roomInfo.label}
        </span>
        <span className="room-card-id">ID: {room_id}</span>
      </div>
      <div className="room-card-right">
        <span className="room-card-time">
          {new Date(created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
        <button
          className="btn-join"
          disabled={isJoining}
          onClick={(e) => { e.stopPropagation(); if (!isJoining) onJoin(room_id); }}
        >
          {isJoining ? 'Подключение...' : 'Войти'}
        </button>
      </div>
    </div>
  );
}

const ROOM_LABELS = {
  quick: { label: 'Быстрая игра', badge: 'quick', icon: '⚡' },
  friend: { label: 'Вызов другу', badge: 'friend', icon: '🔗' },
  ai: { label: 'Игра с ботом', badge: 'ai', icon: '🤖' },
};
const DEFAULT_ROOM = { label: 'Игра', badge: 'quick', icon: '⚡' };

function getRoomInfo(type) {
  return ROOM_LABELS[type] || DEFAULT_ROOM;
}