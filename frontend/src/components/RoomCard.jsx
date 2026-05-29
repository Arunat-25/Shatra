import { useTranslation } from 'react-i18next';
import { formatTimeControlLabel } from '../utils';

function formatCreatorDisplay(creatorUsername, t) {
  if (creatorUsername) return creatorUsername;
  return t('lobby.anonymous');
}

export default function RoomCard({ room, isJoining, onJoin }) {
  const { t } = useTranslation();
  const { room_id, type, time_control, increment, creator_username } = room;
  const roomInfo = getRoomInfo(type, t);
  const timeLabel = formatTimeControlLabel(time_control, increment);
  const primaryLabel = type === 'public'
    ? formatCreatorDisplay(creator_username, t)
    : roomInfo.label;

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
          <span
            className={`room-card-type-badge ${roomInfo.badge}`}
            title={type === 'public' ? t('lobby.publicRoom') : roomInfo.label}
          >
            {roomInfo.icon}
          </span>
          <span className="room-card-label" title={type === 'public' ? t('lobby.creator') : undefined}>
            {primaryLabel}
          </span>
        </span>
      </div>
      <span
        className={`room-card-time${time_control == null ? ' room-card-time--unlimited' : ''}`}
        title={time_control == null ? t('lobby.noTimer') : undefined}
        aria-label={time_control == null ? t('lobby.noTimer') : undefined}
      >
        {timeLabel}
      </span>
      <div className="room-card-right">
        <span className="room-card-id">{room_id}</span>
        <button
          type="button"
          className="btn-join"
          disabled={isJoining}
          onClick={(e) => { e.stopPropagation(); if (!isJoining) onJoin(room_id); }}
        >
          {isJoining ? '…' : t('lobby.join')}
        </button>
      </div>
    </div>
  );
}

const ROOM_LABELS = {
  public: {
    labelKey: 'lobby.publicRoom',
    badge: 'public',
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
      </svg>
    ),
  },
  private: {
    labelKey: 'lobby.privateRoom',
    badge: 'private',
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    ),
  },
  ai: {
    labelKey: 'lobby.aiRoom',
    badge: 'ai',
    icon: (
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden>
        <rect x="5" y="9" width="14" height="10" rx="2" />
        <path d="M9 9V7a3 3 0 0 1 6 0v2" />
      </svg>
    ),
  },
};
const DEFAULT_ROOM = ROOM_LABELS.public;

function getRoomInfo(type, t) {
  const info = ROOM_LABELS[type] || DEFAULT_ROOM;
  const label = t(info.labelKey);
  return { ...info, label };
}
