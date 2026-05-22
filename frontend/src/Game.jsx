import { useEffect, useCallback, useRef, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { joinRoom } from './api';
import useWebSocket from './hooks/useWebSocket';
import useGameReducer, { GAME_ACTIONS } from './hooks/useGameReducer';
import useMessage from './hooks/useMessage';
import useEscapeKey from './hooks/useEscapeKey';
import BoardGrid from './BoardGrid';
import GameHeader from './components/GameHeader';
import GameInfo from './components/GameInfo';
import WaitingScreen from './components/WaitingScreen';
import GameOverScreen from './components/GameOverScreen';
import DisconnectOverlay from './components/DisconnectOverlay';
import MoveHistory from './components/MoveHistory';
import { COLOR_BLACK, COLOR_WHITE, COLOR_WHITE_INCL, MSG_WARNING, MSG_ERROR } from './constants';
import { getClientId } from './utils';

export default function Game() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const roomId = searchParams.get('room');
  const playerId = searchParams.get('player') ? parseInt(searchParams.get('player')) : null;
  const modeFriend = searchParams.get('mode') === 'friend';
  const modeAi = searchParams.get('mode') === 'ai';

  const { state, dispatch, handleServerMessage, deselectPiece } = useGameReducer(modeAi);
  const { message, messageType, showMessage } = useMessage();
  const stateRef = useRef(state);
  stateRef.current = state;

  // Обратный отсчёт при отключении соперника
  useEffect(() => {
    if (!state.opponentDisconnected || state.disconnectCountdown <= 0) return;
    const timer = setInterval(() => {
      dispatch({ type: GAME_ACTIONS.DISCONNECT_TICK });
    }, 1000);
    return () => clearInterval(timer);
  }, [state.opponentDisconnected, state.disconnectCountdown]);

  // Оборачиваем handleServerMessage для показа сообщений пользователю
  const handleWsMessage = useCallback((data) => {
    const msg = handleServerMessage(data);
    if (msg) showMessage(msg.text, msg.type);
  }, [handleServerMessage, showMessage]);

  const handleWsError = useCallback((errMsg) => {
    showMessage(errMsg, MSG_ERROR);
  }, [showMessage]);

  const { send } = useWebSocket(roomId, playerId, handleWsMessage, handleWsError);

  // Подключение для зрителя
  useEffect(() => {
    if (roomId && playerId === null) {
      joinRoom(roomId).catch((e) => {
        showMessage(e.message, MSG_ERROR);
      });
    }
  }, [roomId, playerId, showMessage]);

  // Цвет игрока
  useEffect(() => {
    dispatch({
      type: 'SET_MY_COLOR',
      payload: playerId === null || playerId === 2 ? COLOR_BLACK : COLOR_WHITE,
    });
  }, [playerId, dispatch]);

  // Escape для отмены выбора фигуры
  useEscapeKey(state.moveFrom !== null, deselectPiece);

  const goToLobby = useCallback(() => navigate('/'), [navigate]);

  const handleCellClick = useCallback((positionNum) => {
    if (state.gameOver || state.aiThinking) return;
    const s = stateRef.current;

    if (s.moversColor !== s.myColor) {
      showMessage('Не ваш ход!', MSG_WARNING);
      return;
    }

    if (s.moveFrom === null) {
      const piece = s.board[positionNum];
      if (!piece) return;
      const pieceColor = piece.includes(COLOR_WHITE_INCL) ? COLOR_WHITE : COLOR_BLACK;
      if (pieceColor !== s.myColor) return;

      dispatch({ type: GAME_ACTIONS.SET_MOVE_FROM, payload: positionNum });
      send({
        position: `position${positionNum}`,
        movers_color: s.moversColor,
        board: s.board,
        position_for_mandatory_capture: s.posForMandatoryCapture,
      });
      return;
    }

    if (s.moveFrom === positionNum) {
      deselectPiece();
      return;
    }

    // Совершаем ход
    dispatch({
      type: GAME_ACTIONS.SET_LAST_MOVE,
      payload: { from: s.moveFrom, to: positionNum },
    });
    send({
      move_from: `position${s.moveFrom}`,
      move_to: `position${positionNum}`,
      movers_color: s.moversColor,
      board: s.board,
      position_for_mandatory_capture: s.posForMandatoryCapture,
    });
    deselectPiece();
  }, [state.gameOver, state.aiThinking, showMessage, send, dispatch, deselectPiece]);

  const skipTurn = useCallback(() => {
    const s = stateRef.current;
    send({
      move_from: 'position0',
      move_to: 'position0',
      movers_color: s.moversColor,
      board: s.board,
      position_for_mandatory_capture: s.posForMandatoryCapture,
    });
    dispatch({ type: GAME_ACTIONS.CLEAR_CAN_PASS });
  }, [send, dispatch]);

  // Управление историей ходов
  const viewHistoryMove = useCallback((idx) => {
    dispatch({ type: GAME_ACTIONS.VIEW_HISTORY_MOVE, payload: idx });
  }, [dispatch]);

  const exitHistory = useCallback(() => {
    // Возвращаем актуальное состояние доски
    const s = stateRef.current;
    // Без доски в payload просто убираем флаг VIEW,
    // но нужно восстановить доску из последнего MOVE_MADE
    dispatch({ type: GAME_ACTIONS.EXIT_HISTORY });
    // После EXIT_HISTORY нужно вернуть board к последнему состоянию.
    // Так как мы храним исходную доску только в последнем entry,
    // используем fallback: dispatch повторный SET_MOVE_HISTORY не меняет board
  }, [dispatch]);

  // Обработка Escape в режиме истории
  useEscapeKey(state.viewingHistoryIndex !== null, exitHistory);

  // Блокируем клики по доске в режиме просмотра истории
  const handleCellClickWrapped = useCallback((positionNum) => {
    if (state.viewingHistoryIndex !== null) return;  // режим истории — клики заблокированы
    handleCellClick(positionNum);
  }, [state.viewingHistoryIndex, handleCellClick]);

  const [showGameOver, setShowGameOver] = useState(true);
  // Сбросить showGameOver при gameOver = false (новая игра)
  useEffect(() => {
    if (!state.gameOver) setShowGameOver(true);
  }, [state.gameOver]);

  // Закрыть GameOverScreen и показать доску с историей
  const closeGameOver = useCallback(() => {
    setShowGameOver(false);
  }, []);

  if (state.waiting) {
    return (
      <WaitingScreen
        roomId={roomId}
        playerId={playerId}
        modeFriend={modeFriend}
        modeAi={modeAi}
        joiningError={state.joiningError}
      />
    );
  }

  return (
    <div className="game-page">
      <div className="game-screen">
        <GameHeader
          myColor={state.myColor}
          moversColor={state.moversColor}
          aiThinking={state.aiThinking}
          onGoToLobby={goToLobby}
          timer={state.timer}
          timeControl={state.timeControl}
          playerId={getClientId()}
        />

        <div className={`board ${state.gameOver || state.opponentDisconnected ? 'disabled' : ''} ${state.aiThinking ? 'board-ai-thinking' : ''}`}>
          {state.opponentDisconnected && (
            <DisconnectOverlay disconnectCountdown={state.disconnectCountdown} />
          )}
          <BoardGrid
            board={state.board}
            onCellClick={handleCellClickWrapped}
            moveFrom={state.moveFrom}
            highlightedEssential={state.highlightedEssential}
            highlightedCaptured={state.highlightedCaptured}
            lastMove={state.lastMove}
            historyFrom={state.historyFrom}
            historyTo={state.historyTo}
          />
        </div>

        {message && (
          <div className={`message message-${messageType}`}>{message}</div>
        )}

        <GameInfo
          whiteCount={state.whiteCount}
          blackCount={state.blackCount}
          roomId={roomId}
          modeAi={modeAi}
          canPass={state.canPass}
          gameOver={state.gameOver}
          onSkipTurn={skipTurn}
          onCopyLink={() => showMessage('Ссылка скопирована!', 'success')}
          myColor={state.myColor}
        />
      </div>

      <MoveHistory
        movesHistory={state.movesHistory}
        viewingHistoryIndex={state.viewingHistoryIndex}
        onViewMove={viewHistoryMove}
        onExitHistory={exitHistory}
      />

      {/* GameOver overlay — поверх доски, не заменяет её */}
      {state.gameOver && showGameOver && (
        <GameOverScreen
          winner={state.winner}
          myColor={state.myColor}
          modeAi={modeAi}
          reason={state.gameOverReason}
          onGoToLobby={() => navigate('/', { replace: true })}
          onViewHistory={closeGameOver}
        />
      )}
    </div>
  );
}