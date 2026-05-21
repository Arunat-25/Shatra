import { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { joinRoom } from './api';
import ShatraPiece from './ShatraPiece';

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

  const boardRef = useRef(board);
  boardRef.current = board;
  const myColorRef = useRef(myColor);
  myColorRef.current = myColor;
  const moversColorRef = useRef(moversColor);
  moversColorRef.current = moversColor;
  const posForMandatoryCaptureRef = useRef(posForMandatoryCapture);
  posForMandatoryCaptureRef.current = posForMandatoryCapture;
  const wsRef = useRef(null);

  const showMessage = useCallback((text, type = 'инфо') => {
    setMessage(text);
    setMessageType(type);
    if (type === 'инфо' || type === 'предупреждение') {
      setTimeout(() => setMessage(''), 3000);
    }
  }, []);

  const handleServerMessage = useCallback((data) => {
    if (data.status === 'waiting') {
      setWaiting(true);
      return;
    }

    if (data.game_over) {
      setGameOver(true);
      showMessage(`Игра окончена: ${data.winner || ''}`, 'победа');
      if (data.desk) setBoard(convertKeys(data.desk));
      return;
    }

    // Ход или сообщение
    if (data.message && data.desk) {
      setBoard(convertKeys(data.desk));
      if (data.movers_color) setMoversColor(data.movers_color);
      showMessage(data.message, 'инфо');
      setPosForMandatoryCapture(data.position_for_mandatory_capture || null);
      setCanPass(!!data.opportunity_pass_the_move);
      setHighlightedEssential([]);
      setHighlightedCaptured([]);
      return;
    }

    // Хинты (без message — это не ход)
    if (data.essential_positions !== undefined && !data.message) {
      setHighlightedEssential(data.essential_positions || []);
      setHighlightedCaptured(data.captured_pieces || []);
      return;
    }

    // Старт игры
    if (data.desk && !data.message) {
      setMoversColor(data.movers_color || 'белый');
      setBoard(convertKeys(data.desk));
      setWaiting(false);
      setHighlightedEssential([]);
      setHighlightedCaptured([]);
      showMessage('Игра началась!', 'инфо');
      return;
    }
  }, [showMessage]);

  // WebSocket
  useEffect(() => {
    if (!roomId) return;
    
    const openWebSocket = () => {
      // Передаём playerId как query-параметр, чтобы сервер знал, кто подключается
      const ws = new WebSocket(`ws://${window.location.host}/ws/${roomId}/?player=${playerId || ''}`);
      wsRef.current = ws;
      ws.onmessage = (event) => handleServerMessage(JSON.parse(event.data));
      ws.onclose = (event) => {
        if (event.code !== 1000) {
          setMessage('Соединение разорвано');
          setMessageType('ошибка');
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
      if (wsRef.current) wsRef.current.close();
    };
  }, [roomId, playerId, handleServerMessage]);

  // Цвет от playerId
  useEffect(() => {
    setMyColor(playerId === null || playerId === 2 ? 'черный' : 'белый');
  }, [playerId]);

  const handleCellClick = useCallback((positionNum) => {
    if (gameOver) return;
    if (moversColorRef.current !== myColorRef.current) {
      showMessage('Не ваш ход!', 'предупреждение');
      return;
    }
    if (moveFrom === null) {
      const piece = boardRef.current[positionNum];
      if (!piece) return;
      const pieceColor = piece.includes('бел') ? 'белый' : 'черный';
      if (pieceColor === myColorRef.current) {
        setMoveFrom(positionNum);
        setHighlightedEssential([]);
        setHighlightedCaptured([]);
        if (wsRef.current) {
          wsRef.current.send(JSON.stringify({
            position: `position${positionNum}`,
            movers_color: moversColorRef.current,
            board: boardRef.current,
            position_for_mandatory_capture: posForMandatoryCaptureRef.current,
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
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({
        move_from: `position${moveFrom}`,
        move_to: `position${positionNum}`,
        movers_color: moversColorRef.current,
        board: boardRef.current,
        position_for_mandatory_capture: posForMandatoryCaptureRef.current,
      }));
    }
    setHighlightedEssential([]);
    setHighlightedCaptured([]);
    setMoveFrom(null);
  }, [moveFrom, gameOver, showMessage]);

  const sendPassTheMove = () => {
    if (wsRef.current) {
      wsRef.current.send(JSON.stringify({
        move_from: 'position0',
        move_to: 'position0',
        movers_color: moversColorRef.current,
        board: boardRef.current,
        position_for_mandatory_capture: posForMandatoryCaptureRef.current,
      }));
    }
    setCanPass(false);
  };

  if (waiting) {
    // Поле со ссылкой показываем при прямом заходе (без playerId)
    // или при вызове друга (mode=friend)
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
                  type="text"
                  readOnly
                  value={`${window.location.origin}/game?room=${roomId}`}
                  onClick={(e) => e.target.select()}
                />
                <button className="btn-refresh" onClick={() => {
                  const inp = document.querySelector('.waiting-link-input');
                  if (inp) { inp.select(); navigator.clipboard.writeText(inp.value); }
                }}>Копировать</button>
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
          <button className="btn-pass" onClick={sendPassTheMove}>Передать ход</button>
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

function getPieceType(pieceStr) {
  if (pieceStr.includes('бий')) return 'бий';
  if (pieceStr.includes('батыр')) return 'батыр';
  return 'шатра';
}

function getPieceColor(pieceStr) {
  return pieceStr.includes('бел') ? 'белый' : 'черный';
}

function BoardGrid({ board, onCellClick, moveFrom, highlightedEssential = [], highlightedCaptured = [] }) {
  const renderCell = (id, className) => {
    const isEssential = highlightedEssential.includes(id);
    const isCaptured = highlightedCaptured.includes(id);
    const classes = [
      'kletka',
      className,
      board[id] ? 'has-piece' : '',
      moveFrom === id ? 'highlight-black' : '',
      isEssential ? 'highlight-essential' : '',
      isCaptured ? 'highlight-captured' : '',
    ].filter(Boolean).join(' ');
    
    return (
      <div
        key={id}
        id={`position${id}`}
        className={classes}
        onClick={() => onCellClick(id)}
      >
        {board[id] && (
          <div className="image-in-kletka">
            <ShatraPiece 
              type={getPieceType(board[id])} 
              color={getPieceColor(board[id])}
              isSelected={moveFrom === id}
              isTarget={isCaptured}
            />
          </div>
        )}
      </div>
    );
  };

  return (
    <>
      <div className="field-of-reserve">
        <div className="row">
          {renderCell(1, 'nechetnaya')}{renderCell(2, 'chetnaya')}{renderCell(3, 'nechetnaya')}
        </div>
        <div className="row">
          {renderCell(4, 'chetnaya')}{renderCell(5, 'nechetnaya')}{renderCell(6, 'chetnaya')}
        </div>
        <div className="row">
          {renderCell(7, 'nechetnaya')}{renderCell(8, 'chetnaya')}{renderCell(9, 'nechetnaya')}
        </div>
      </div>
      <div className="field-of-queen">{renderCell(10, 'chetnaya')}</div>
      <div className="main-field">
        <div className="row">
          {renderCell(11, 'nechetnaya')}{renderCell(12, 'chetnaya')}{renderCell(13, 'nechetnaya')}
          {renderCell(14, 'chetnaya')}{renderCell(15, 'nechetnaya')}{renderCell(16, 'chetnaya')}{renderCell(17, 'nechetnaya')}
        </div>
        <div className="row">
          {renderCell(18, 'chetnaya')}{renderCell(19, 'nechetnaya')}{renderCell(20, 'chetnaya')}
          {renderCell(21, 'nechetnaya')}{renderCell(22, 'chetnaya')}{renderCell(23, 'nechetnaya')}{renderCell(24, 'chetnaya')}
        </div>
        <div className="row">
          {renderCell(25, 'nechetnaya')}{renderCell(26, 'chetnaya')}{renderCell(27, 'nechetnaya')}
          {renderCell(28, 'chetnaya')}{renderCell(29, 'nechetnaya')}{renderCell(30, 'chetnaya')}{renderCell(31, 'nechetnaya')}
        </div>
      </div>
      <div className="main-field">
        <div className="row">
          {renderCell(32, 'chetnaya')}{renderCell(33, 'nechetnaya')}{renderCell(34, 'chetnaya')}
          {renderCell(35, 'nechetnaya')}{renderCell(36, 'chetnaya')}{renderCell(37, 'nechetnaya')}{renderCell(38, 'chetnaya')}
        </div>
        <div className="row">
          {renderCell(39, 'nechetnaya')}{renderCell(40, 'chetnaya')}{renderCell(41, 'nechetnaya')}
          {renderCell(42, 'chetnaya')}{renderCell(43, 'nechetnaya')}{renderCell(44, 'chetnaya')}{renderCell(45, 'nechetnaya')}
        </div>
        <div className="row">
          {renderCell(46, 'chetnaya')}{renderCell(47, 'nechetnaya')}{renderCell(48, 'chetnaya')}
          {renderCell(49, 'nechetnaya')}{renderCell(50, 'chetnaya')}{renderCell(51, 'nechetnaya')}{renderCell(52, 'chetnaya')}
        </div>
      </div>
      <div className="field-of-queen">{renderCell(53, 'chetnaya')}</div>
      <div className="field-of-reserve">
        <div className="row">
          {renderCell(54, 'nechetnaya')}{renderCell(55, 'chetnaya')}{renderCell(56, 'nechetnaya')}
        </div>
        <div className="row">
          {renderCell(57, 'chetnaya')}{renderCell(58, 'nechetnaya')}{renderCell(59, 'chetnaya')}
        </div>
        <div className="row">
          {renderCell(60, 'nechetnaya')}{renderCell(61, 'chetnaya')}{renderCell(62, 'nechetnaya')}
        </div>
      </div>
    </>
  );
}