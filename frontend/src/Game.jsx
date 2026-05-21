import { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { joinRoom } from './api';
import BoardGrid from './BoardGrid';

export default function Game() {
  const [searchParams] = useSearchParams();
  const roomId = searchParams.get('room');
  const playerParam = searchParams.get('player');
  const playerId = playerParam ? parseInt(playerParam) : null;
  const modeFriend = searchParams.get('mode') === 'friend';

  const [waiting, setWaiting] = useState(true);
  const [joiningError, setJoiningError] = useState('');
  const [myColor, setMyColor] = useState(null);
  const [moversColor, setMoversColor] = useState(null);
  const [board, setBoard] = useState({});
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');
  const [posForMandatoryCapture, setPosForMandatoryCapture] = useState(null);
  const [moveFrom, setMoveFrom] = useState(null);
  const [canPass, setCanPass] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [highlightedEssential, setHighlightedEssential] = useState([]);
  const [highlightedCaptured, setHighlightedCaptured] = useState([]);

  // Единый ref для отслеживания текущих значений без ререндера
  const stateRef = useRef({ board, myColor, moversColor, posForMandatoryCapture });
  stateRef.current = { board, myColor, moversColor, posForMandatoryCapture };

  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const linkInputRef = useRef(null);
  const intentionalCloseRef = useRef(false);

  const showMessage = useCallback((text, type = 'info') => {
    setMessage(text);
    setMessageType(type);
    if (type === 'info' || type === 'warning') {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => setMessage(''), 3000);
    }
  }, []);

  // Cleanup на размонтирование
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const handleServerMessage = useCallback((data) => {
    if (data.status === 'waiting') {
      setWaiting(true);
      return;
    }

    if (data.game_over) {
      setGameOver(true);
      showMessage(`Игра окончена: ${data.winner || ''}`, 'victory');
      if (data.desk) setBoard(convertKeys(data.desk));
      return;
    }

    if (data.message && data.desk) {
      setBoard(convertKeys(data.desk));
      if (data.movers_color) setMoversColor(data.movers_color);
      showMessage(data.message, 'info');
      setPosForMandatoryCapture(data.position_for_mandatory_capture || null);
      setCanPass(!!data.opportunity_pass_the_move);
      setHighlightedEssential([]);
      setHighlightedCaptured([]);
      return;
    }

    if (data.essential_positions !== undefined && !data.message) {
      setHighlightedEssential(data.essential_positions || []);
      setHighlightedCaptured(data.captured_pieces || []);
      return;
    }

    if (data.desk && !data.message) {
      setMoversColor(data.movers_color || 'белый');
      setBoard(convertKeys(data.desk));
      setWaiting(false);
      setHighlightedEssential([]);
      setHighlightedCaptured([]);
      showMessage('Игра началась!', 'info');
      return;
    }
  }, [showMessage]);

  // WebSocket
  useEffect(() => {
    if (!roomId) return;
    
    const openWebSocket = () => {
      const ws = new WebSocket(`ws://${window.location.host}/ws/${roomId}/?player=${playerId || ''}`);
      wsRef.current = ws;
      ws.onmessage = (event) => handleServerMessage(JSON.parse(event.data));
      ws.onclose = (event) => {
        if (event.code !== 1000 && !intentionalCloseRef.current) {
          setMessage('Соединение разорвано');
          setMessageType('error');
        }
      };
    };

    if (playerId === null) {
      joinRoom(roomId).then(openWebSocket).catch((e) => {
        setJoiningError(e.message);
      });
    } else {
      openWebSocket();
    }

    return () => {
      intentionalCloseRef.current = true;
      if (wsRef.current) wsRef.current.close();
    };
  }, [roomId, playerId, handleServerMessage]);

  // Цвет от playerId
  useEffect(() => {
    setMyColor(playerId === null || playerId === 2 ? 'черный' : 'белый');
  }, [playerId]);

  const handleCellClick = useCallback((positionNum) => {
    if (gameOver) return;
    const s = stateRef.current;
    if (s.moversColor !== s.myColor) {
      showMessage('Не ваш ход!', 'warning');
      return;
    }
    if (moveFrom === null) {
      const piece = s.board[positionNum];
      if (!piece) return;
      const pieceColor = piece.includes('бел') ? 'белый' : 'черный';
      if (pieceColor === s.myColor) {
        setMoveFrom(positionNum);
        setHighlightedEssential([]);
        setHighlightedCaptured([]);
        if (wsRef.current) {
          wsRef.current.send(JSON.stringify({
            position: `position${positionNum}`,
            movers_color: s.moversColor,
            board: s.board,
            position_for_mandatory_capture: s.posForMandatoryCapture,
          }));
        }
      }
      return;
    }
    if (moveFrom === positionNum) {
      setMoveFrom(null);
      setHighlightedEssential([]);
      setHighlightedCaptured([]);
      return;
    }
    const s2 = stateRef.current;
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({
        move_from: `position${moveFrom}`,
        move_to: `position${positionNum}`,
        movers_color: s2.moversColor,
        board: s2.board,
        position_for_mandatory_capture: s2.posForMandatoryCapture,
      }));
    }
    setHighlightedEssential([]);
    setHighlightedCaptured([]);
    setMoveFrom(null);
  }, [moveFrom, gameOver, showMessage]);

  const skipTurn = () => {
    const s = stateRef.current;
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({
        move_from: 'position0',
        move_to: 'position0',
        movers_color: s.moversColor,
        board: s.board,
        position_for_mandatory_capture: s.posForMandatoryCapture,
      }));
    }
    setCanPass(false);
  };

  const copyLink = useCallback(() => {
    if (linkInputRef.current) {
      linkInputRef.current.select();
      navigator.clipboard.writeText(linkInputRef.current.value);
    }
  }, []);

  if (waiting) {
    const showLink = playerId === null || modeFriend;
    return (
      <div className="waiting-screen">
        <div className="waiting-content">
          <div className="waiting-spinner"></div>
          <h2 className="waiting-title">Ожидание соперника</h2>
          {showLink && (
            <>
              <p className="waiting-subtitle">Поделитесь ссылкой, чтобы пригласить друга</p>
              <div className="waiting-link-container">
                <input
                  className="waiting-link-input"
                  ref={linkInputRef}
                  type="text"
                  readOnly
                  value={`${window.location.origin}/game?room=${roomId}`}
                  onClick={() => linkInputRef.current?.select()}
                />
                <button className="btn-refresh" onClick={copyLink}>Копировать</button>
              </div>
            </>
          )}
          <p className="waiting-hint">Игра начнётся, когда второй игрок присоединится</p>
          {joiningError && (
            <div className="error-container"><p>{joiningError}</p></div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="game-page">
      <div className="game-screen">
        <div className="game-header">
          <div className="header-left">
            <span className="game-title">Шатра</span>
            <div className="player-info">
              <span className={myColor === 'белый' ? 'color-white' : 'color-black'}>
                Вы: {myColor === 'белый' ? '⚪ Белые' : '⚫ Черные'}
              </span>
            </div>
          </div>
          <div className="header-right">
            <div className={`turn-indicator ${moversColor === 'белый' ? 'turn-white' : 'turn-black'}`}>
              Ход: {moversColor === 'белый' ? '⚪ Белых' : '⚫ Черных'}
            </div>
          </div>
        </div>

        <div className={`board ${gameOver ? 'disabled' : ''}`}>
          <BoardGrid 
            board={board} 
            onCellClick={handleCellClick} 
            moveFrom={moveFrom} 
            highlightedEssential={highlightedEssential}
            highlightedCaptured={highlightedCaptured}
          />
        </div>

        {message && (
          <div className={`message message-${messageType}`}>{message}</div>
        )}

        {canPass && !gameOver && (
          <button className="btn-pass" onClick={skipTurn}>Передать ход</button>
        )}

        <div className="game-info-bottom">
          <span>Комната: {roomId}</span>
        </div>
      </div>
    </div>
  );
}

function convertKeys(serverBoard) {
  const result = {};
  for (const [key, value] of Object.entries(serverBoard)) {
    result[parseInt(key)] = value;
  }
  return result;
}