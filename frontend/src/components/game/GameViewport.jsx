import { useTranslation } from 'react-i18next';
import BoardGrid from '../../BoardGrid';
import DisconnectOverlay from '../DisconnectOverlay';
import MoveHistory from '../MoveHistory';
import PlayerBar from '../PlayerBar';

export default function GameViewport({
  boardTop,
  boardBottom,
  state,
  isBoardBlocked,
  onCellClick,
  actionsBar,
  moveHistoryProps,
}) {
  const { t } = useTranslation();

  return (
    <section className="game-viewport-first" aria-label={t('game.boardAria')}>
      <div className="game-screen-fit">
        <PlayerBar
          position="top"
          color={boardTop}
          playersInfo={state.playersInfo}
          timer={state.timer}
          moversColor={state.moversColor}
          myColor={state.myColor}
          timeControl={state.timeControl}
          countsByType={state.countsByType}
        />
        <div className="room-board">
          <div
            className={[
              'board',
              isBoardBlocked ? 'disabled' : '',
              (state.aiThinking || state.opponentDisconnected) ? 'board-dimmed' : '',
              state.aiThinking ? 'board-ai-thinking' : '',
            ].filter(Boolean).join(' ')}
          >
            {state.opponentDisconnected && (
              <DisconnectOverlay disconnectCountdown={state.disconnectCountdown} />
            )}
            <BoardGrid
              board={state.board}
              onCellClick={onCellClick}
              moveFrom={state.moveFrom}
              highlightedEssential={state.highlightedEssential}
              highlightedCaptured={state.highlightedCaptured}
              lastMove={state.lastMove}
              historyFrom={state.historyFrom}
              historyTo={state.historyTo}
              myColor={state.myColor}
            />
          </div>
        </div>

        <PlayerBar
          position="bottom"
          color={boardBottom}
          playersInfo={state.playersInfo}
          timer={state.timer}
          moversColor={state.moversColor}
          myColor={state.myColor}
          timeControl={state.timeControl}
          countsByType={state.countsByType}
        />
      </div>

      {actionsBar}

      <div className="move-history-slot move-history-slot--viewport">
        <MoveHistory {...moveHistoryProps} />
      </div>
    </section>
  );
}
