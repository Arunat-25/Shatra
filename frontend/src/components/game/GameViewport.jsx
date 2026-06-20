import { useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { probeBoardLayout } from '../../debug/boardLayoutProbe';
import useDevLayoutProbe from '../../hooks/useDevLayoutProbe';
import { isDevProbeEnabled } from '../../debug/devProbe';
import { useLiteUi } from '../../context/LiteUiContext';
import { computeLocalHints } from '../../engine/localHints';
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
  const { enabled: liteUi } = useLiteUi();

  const getDragLegalDests = useCallback(
    (fromCell) => computeLocalHints(state, fromCell).essential,
    [state],
  );

  const clockProps = {
    timer: state.timer,
    timerSyncedAt: state.timerSyncedAt,
    moversColor: state.moversColor,
    timeControl: state.timeControl,
    gameOver: state.gameOver,
    waiting: state.waiting,
  };

  useDevLayoutProbe(() => {
    if (state.waiting) return;
    probeBoardLayout('state-change', {
      moveFrom: state.moveFrom,
      aiThinking: state.aiThinking,
      liteUi,
    });
  }, [state.waiting, state.moveFrom, state.aiThinking, state.myColor, liteUi]);

  useEffect(() => {
    if (!isDevProbeEnabled() || state.waiting) return undefined;
    const slot = document.querySelector('.room-board');
    if (!slot) return undefined;
    const ro = new ResizeObserver(() => probeBoardLayout('resize', { liteUi }));
    ro.observe(slot);
    return () => ro.disconnect();
  }, [state.waiting, liteUi]);

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
                    liteUi ? 'board--lite' : '',
                    isBoardBlocked ? 'disabled' : '',
                    !liteUi && state.aiThinking ? 'board-dimmed board-ai-thinking' : '',
                  ].filter(Boolean).join(' ')}
                >
                  <BoardSurface
                    board={state.board}
                    onCellClick={onCellClick}
                    moveFrom={state.moveFrom}
                    getDragLegalDests={getDragLegalDests}
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
