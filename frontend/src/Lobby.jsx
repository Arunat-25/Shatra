import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRoom, listRooms, joinRoom } from './api';
import useRoomPolling from './hooks/useRoomPolling';
import RoomCard from './components/RoomCard';
import GameEmblem from './components/GameEmblem';
import TimerPicker from './components/TimerPicker';
import { ROOM_QUICK, ROOM_FRIEND, ROOM_AI, POLL_INTERVAL } from './constants';

export default function Lobby() {
  const navigate = useNavigate();
  const { rooms, error, refreshing, setError, fetchRooms } = useRoomPolling(listRooms, POLL_INTERVAL);
  const [joinerRoomId, setJoinerRoomId] = useState(null);
  const [showTimerPicker, setShowTimerPicker] = useState(false);
  const [pickerMode, setPickerMode] = useState(null); // 'quick' | 'friend'

  const dismissError = () => setError('');

  const handleQuick = () => {
    setPickerMode('quick');
    setShowTimerPicker(true);
  };

  const handleFriend = () => {
    setPickerMode('friend');
    setShowTimerPicker(true);
  };

  const handleAI = async () => {
    setError('');
    try {
      const data = await createRoom(ROOM_AI, null, null);
      navigate(`/game?room=${data.room_id}&player=1&mode=ai`);
    } catch (e) {
      setError(e.message);
    }
  };

  const finishCreate = async (timeValue, incrementValue) => {
    setError('');
    try {
      const type = pickerMode === 'friend' ? ROOM_FRIEND : ROOM_QUICK;
      const mode = pickerMode === 'friend' ? 'friend' : '';
      const data = await createRoom(type, timeValue, incrementValue);
      const modeParam = mode ? `&mode=${mode}` : '';
      navigate(`/game?room=${data.room_id}&player=1${modeParam}`);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleCancelTimer = () => {
    setShowTimerPicker(false);
    setPickerMode(null);
  };

  const handleJoinRoom = async (roomId) => {
    setJoinerRoomId(roomId);
    setError('');
    try {
      await joinRoom(roomId);
      // После успешного join создаём WebSocket через хук
      // Используем колбэк для редиректа
      const ws = new WebSocket(`ws://${window.location.host}/ws/${roomId}/`);
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.status === 'game_started' || msg.movers_color) {
          navigate(`/game?room=${roomId}&player=2`);
        }
      };
      ws.onerror = () => setError('Ошибка подключения к комнате');
    } catch (e) {
      setError(e.message);
      setJoinerRoomId(null);
    }
  };

  const showLoading = refreshing && rooms.length === 0;

  return (
    <div className="lobby-layout">
      <div className="lobby-left">
        <div className="lobby-left-inner">
          <div className="lobby-emblem">
            <GameEmblem size={80} className="lobby-emblem-svg" />
          </div>
          <h1>Шатра</h1>
          <p className="lobby-subtitle">Алтайская народная игра</p>

          {showTimerPicker ? (
            <TimerPicker onFinish={finishCreate} onCancel={handleCancelTimer} />
          ) : (
            <div className="lobby-buttons">
              <button className="btn-lobby btn-battle" onClick={handleQuick}>
                <span className="btn-icon">⚔️</span>
                <span className="btn-text">Создать игру</span>
              </button>
              <button className="btn-lobby btn-ai" onClick={handleAI}>
                <span className="btn-icon">🤖</span>
                <span className="btn-text">Играть с ботом</span>
              </button>
              <button className="btn-lobby btn-invite" onClick={handleFriend}>
                <span className="btn-icon">🔗</span>
                <span className="btn-text">Вызов другу</span>
              </button>
            </div>
          )}

          {error && (
            <div className="error-container">
              <p>{error}</p>
              <button className="error-dismiss" onClick={dismissError} aria-label="Закрыть">✕</button>
            </div>
          )}
        </div>
      </div>

      <div className="lobby-right">
        <div className="lobby-right-header">
          <h2>
            Зал ожидания
            {refreshing && <span className="waiting-spinner-small" />}
          </h2>
          <button className="btn-refresh" onClick={fetchRooms} disabled={refreshing}>
            {refreshing ? 'Обновление...' : 'Обновить'}
          </button>
        </div>
        <div className="rooms-list">
          {!refreshing && rooms.length === 0 ? (
            <div className="rooms-empty">
              <GameEmblem size={60} className="rooms-empty-icon" />
              <p>Нет доступных комнат</p>
              <span>Создайте игру или подождите других игроков</span>
            </div>
          ) : showLoading ? (
            <div className="rooms-empty">
              <div className="waiting-spinner" style={{ width: 36, height: 36, marginBottom: 16 }} />
              <p style={{ color: 'rgba(74, 55, 40, 0.4)' }}>Поиск комнат...</p>
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