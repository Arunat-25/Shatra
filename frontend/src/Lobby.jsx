import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRoom, listRooms, joinRoom, getRoomStatus } from './api';

export default function Lobby() {
  const navigate = useNavigate();
  const [rooms, setRooms] = useState([]);
  const [error, setError] = useState('');
  const [creating, setCreating] = useState(false);
  const [joiningRoom, setJoiningRoom] = useState(null);
  const pollRef = useRef(null);

  const fetchRooms = useCallback(async () => {
    try {
      const data = await listRooms();
      setRooms(data.rooms);
    } catch (e) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    fetchRooms();
    const interval = setInterval(fetchRooms, 10000);
    return () => clearInterval(interval);
  }, [fetchRooms]);

  const handleCreateGame = async () => {
    setCreating(true);
    setError('');
    try {
      const data = await createRoom('quick');
      // Сразу перенаправляем создателя на страницу игры (экран ожидания)
      // Там уже будет поле для копирования ссылки и статус "Ожидание соперника"
      navigate(`/game?room=${data.room_id}&player=1`);
    } catch (e) {
      setError(e.message);
      setCreating(false);
    }
  };

  const handleChallengeFriend = async () => {
    setError('');
    try {
      const data = await createRoom('friend');
      navigate(`/game?room=${data.room_id}&player=1&mode=friend`);
    } catch (e) {
      setError(e.message);
    }
  };

  const handleJoinRoom = async (roomId) => {
    setJoiningRoom(roomId);
    setError('');
    try {
      await joinRoom(roomId);
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
      setJoiningRoom(null);
    }
  };

  return (
    <div className="lobby-layout">
      <div className="lobby-left">
        <div className="lobby-left-inner">
          <div className="lobby-emblem">
            <svg viewBox="0 0 60 60" className="lobby-emblem-svg">
              <circle cx="30" cy="30" r="28" fill="none" stroke="#FFD700" strokeWidth="1.5" opacity="0.4" />
              <path d="M30 8 L34 18 L44 18 L36 24 L38 34 L30 28 L22 34 L24 24 L16 18 L26 18Z" fill="none" stroke="#40E0D0" strokeWidth="1.2" opacity="0.6" />
              <circle cx="30" cy="28" r="3" fill="none" stroke="#FFD700" strokeWidth="1" opacity="0.5" />
            </svg>
          </div>
          <h1>Шатра</h1>
          <p className="lobby-subtitle">Алтайская народная игра</p>
          <div className="lobby-buttons">
            <button
              className="btn-lobby btn-battle"
              onClick={handleCreateGame}
              disabled={creating}
            >
              <span className="btn-icon">⚔️</span>
              <span className="btn-text">{creating ? 'Ожидание соперника...' : 'Создать игру'}</span>
            </button>
            <button
              className="btn-lobby btn-invite"
              onClick={handleChallengeFriend}
            >
              <span className="btn-icon">🔗</span>
              <span className="btn-text">Вызов другу</span>
            </button>
          </div>
          {error && (
            <div className="error-container">
              <p>{error}</p>
            </div>
          )}
        </div>
      </div>

      <div className="lobby-right">
        <div className="lobby-right-header">
          <h2>Зал ожидания</h2>
          <button className="btn-lobby btn-refresh" onClick={fetchRooms}>
            Обновить
          </button>
        </div>
        <div className="rooms-list">
          {rooms.length === 0 ? (
            <div className="rooms-empty">
              <svg viewBox="0 0 40 40" className="rooms-empty-icon">
                <circle cx="20" cy="20" r="18" fill="none" stroke="#FFD700" strokeWidth="0.8" opacity="0.2" />
                <path d="M20 8 Q25 12 28 18 Q15 16 14 24 Q18 28 20 30" fill="none" stroke="#40E0D0" strokeWidth="0.8" opacity="0.3" />
              </svg>
              <p>Нет доступных комнат</p>
              <span>Создайте игру или подождите других игроков</span>
            </div>
          ) : (
            rooms.map((room) => {
              const isJoining = joiningRoom === room.room_id;
              return (
                <div
                  key={room.room_id}
                  className={`room-card ${isJoining ? 'room-card-joining' : ''}`}
                  onClick={() => !isJoining && handleJoinRoom(room.room_id)}
                >
                  <div className="room-card-left">
                    <span className="room-card-type">
                      {room.type === 'quick' ? 'Быстрая игра' : 'Вызов другу'}
                    </span>
                    <span className="room-card-id">ID: {room.room_id}</span>
                  </div>
                  <div className="room-card-right">
                    <span className="room-card-time">
                      {new Date(room.created_at).toLocaleTimeString()}
                    </span>
                    <button
                      className="btn-join"
                      disabled={isJoining}
                      onClick={(e) => { e.stopPropagation(); !isJoining && handleJoinRoom(room.room_id); }}
                    >
                      {isJoining ? '...' : 'Войти'}
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}