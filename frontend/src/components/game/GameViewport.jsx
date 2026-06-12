import React from 'react';
import { useTranslation } from 'react-i18next';
import BoardSurface from '../BoardSurface';
import MoveHistory from '../MoveHistory';
import OpponentDisconnectStatus from './OpponentDisconnectStatus';
import PlayerBar from '../PlayerBar';

export default function GameViewport({
  boardTop,
  boardBottom,
  state,
  isBoardBlocked,
  onCellClick,
  actionsBar,
  moveHistoryProps,
  showRating = false,
}) {
  const { t } = useTranslation();

  const clockProps = {
    timer: state.timer,
    timerSyncedAt: state.timerSyncedAt,
    moversColor: state.moversColor,
    timeControl: state.timeControl,
    gameOver: state.gameOver,
    waiting: state.waiting,
  };

  return (
    <div className="game-viewport-column">
      <section className="game-viewport-first" aria-label={t('game.boardAria')}>
        <div className="game-viewport-fold">
          <div className="game-screen-fit">
            <PlayerBar
              position="top"
              color={boardTop}
              playersInfo={state.playersInfo}
              myColor={state.myColor}
              countsByType={state.countsByType}
              showRating={showRating}
              {...clockProps}
            />
            <div className="room-board-wrap">
              <div className="room-board">
                <div
                  className={[
                    'board',
                    isBoardBlocked ? 'disabled' : '',
                    state.aiThinking ? 'board-dimmed board-ai-thinking' : '',
                  ].filter(Boolean).join(' ')}
                >
                  <BoardSurface
                    board={state.board}
                    onCellClick={onCellClick}
                    moveFrom={state.moveFrom}
                    highlightedEssential={state.highlightedEssential}
                    highlightedCaptured={state.highlightedCaptured}
                    capturedGhostPieces={state.capturedGhostPieces}
                    lastMove={state.lastMove}
                    historyFrom={state.historyFrom}
                    historyTo={state.historyTo}
                    myColor={state.myColor}
                  />
                </div>
              </div>
              {state.opponentDisconnected && (
                <OpponentDisconnectStatus
                  placement="board-edge"
                  disconnectCountdown={state.disconnectCountdown}
                />
              )}
            </div>

            <PlayerBar
              position="bottom"
              color={boardBottom}
              playersInfo={state.playersInfo}
              myColor={state.myColor}
              countsByType={state.countsByType}
              showRating={showRating}
              {...clockProps}
            />
          </div>
        </div>

        {actionsBar && (
          <div className="game-viewport-actions">
            {actionsBar}
          </div>
        )}
      </section>

      <div className="game-viewport-below-fold">
        <div className="move-history-slot move-history-slot--viewport">
          <MoveHistory {...moveHistoryProps} />
        </div>
      </div>
    </div>
  );
}
