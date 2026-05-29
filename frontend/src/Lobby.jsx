import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { createRoom, listRooms, joinRoom } from './api';
import useRoomPolling from './hooks/useRoomPolling';
import RoomCard from './components/RoomCard';
import GameEmblem from './components/GameEmblem';
import GameSetupPicker from './components/GameSetupPicker';
import { ROOM_PUBLIC, ROOM_PRIVATE, ROOM_AI, POLL_INTERVAL } from './constants';

export default function Lobby() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { rooms, error, refreshing, dismissError, setExternalError, fetchRooms } = useRoomPolling(listRooms, POLL_INTERVAL);
  const [joinerRoomId, setJoinerRoomId] = useState(null);
  const [showSetup, setShowSetup] = useState(false);
  const [pickerMode, setPickerMode] = useState(null);

  const lobbyActions = [
    {
      id: 'public',
      className: 'action-card--play',
      label: t('lobby.createGame'),
      desc: t('lobby.createGameDesc'),
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
      ),
    },
    {
      id: 'ai',
      className: 'action-card--ai',
      label: t('lobby.playAi'),
      desc: t('lobby.playAiDesc'),
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <rect x="4" y="8" width="16" height="12" rx="2" />
          <path d="M9 8V6a3 3 0 0 1 6 0v2" />
          <circle cx="9" cy="14" r="1" fill="currentColor" />
          <circle cx="15" cy="14" r="1" fill="currentColor" />
        </svg>
      ),
    },
    {
      id: 'private',
      className: 'action-card--private',
      label: t('lobby.inviteFriend'),
      desc: t('lobby.inviteFriendDesc'),
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
          <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
          <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
        </svg>
      ),
    },
  ];

  const startSetup = (mode) => {
    setPickerMode(mode);
    setShowSetup(true);
  };

  const finishCreate = async (timeValue, incrementValue, colorPref) => {
    dismissError();
    try {
      const type =
        pickerMode === 'private' ? ROOM_PRIVATE : pickerMode === 'ai' ? ROOM_AI : ROOM_PUBLIC;
      const mode = pickerMode === 'private' ? 'private' : pickerMode === 'ai' ? 'ai' : '';
      const data = await createRoom(type, timeValue, incrementValue, colorPref);
      const modeParam = mode ? `?mode=${mode}` : '';
      navigate(`/${data.room_id}${modeParam}`);
    } catch (e) {
      setExternalError(e.message);
    }
  };

  const handleCancelSetup = () => {
    setShowSetup(false);
    setPickerMode(null);
  };

  const handleJoinRoom = async (roomId) => {
    setJoinerRoomId(roomId);
    dismissError();
    try {
      await joinRoom(roomId);
      navigate(`/${roomId}`);
    } catch (e) {
      setExternalError(e.message);
      setJoinerRoomId(null);
    }
  };

  const handleAction = (id) => {
    if (id === 'ai') startSetup('ai');
    else startSetup(id === 'private' ? 'private' : 'public');
  };

  const showLoading = refreshing && rooms.length === 0;

  return (
    <div className="lobby-layout">
      <div className="lobby-left">
        <div className="lobby-left-inner">
          <div className="lobby-emblem">
            <GameEmblem size={72} className="lobby-emblem-svg" />
          </div>
          <h1>{t('lobby.title')}</h1>
          <p className="lobby-subtitle">{t('lobby.subtitle')}</p>

          {showSetup ? (
            <GameSetupPicker
              aiOnly={pickerMode === 'ai'}
              onFinish={finishCreate}
              onCancel={handleCancelSetup}
            />
          ) : (
            <div className="lobby-buttons">
              {lobbyActions.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  className={`action-card ${action.className}`}
                  onClick={() => handleAction(action.id)}
                >
                  <span className="action-card__icon">{action.icon}</span>
                  <span className="action-card__body">
                    <strong>{action.label}</strong>
                    <span>{action.desc}</span>
                  </span>
                  <span className="action-card__arrow" aria-hidden>→</span>
                </button>
              ))}
            </div>
          )}

          {error && (
            <div className="error-container">
              <p>{error}</p>
              <button type="button" className="error-dismiss" onClick={dismissError} aria-label={t('lobby.closeError')}>✕</button>
            </div>
          )}
        </div>
      </div>

      <div className="lobby-right">
        <div className="lobby-right-header">
          <h2>
            {t('lobby.waitingHall')}
            {refreshing && <span className="waiting-spinner-small" />}
          </h2>
          <button type="button" className="btn-lobby btn-refresh" onClick={fetchRooms} disabled={refreshing}>
            {refreshing ? '…' : t('lobby.refresh')}
          </button>
        </div>
        <div className="rooms-list">
          {!refreshing && rooms.length === 0 ? (
            <div className="rooms-empty">
              <GameEmblem size={48} className="rooms-empty-icon" />
              <p>{t('lobby.noRooms')}</p>
              <span>{t('lobby.noRoomsHint')}</span>
            </div>
          ) : showLoading ? (
            <div className="rooms-empty">
              <div className="waiting-spinner" style={{ width: 36, height: 36, marginBottom: 16 }} />
              <p>{t('lobby.searchingRooms')}</p>
            </div>
          ) : (
            rooms.map((room) => (
              <RoomCard
                key={room.room_id}
                room={room}
                isJoining={joinerRoomId === room.room_id}
                onJoin={handleJoinRoom}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
