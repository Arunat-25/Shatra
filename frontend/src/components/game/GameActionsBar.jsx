import { useTranslation } from 'react-i18next';
import GameControls from '../GameControls';
import GameResultActions from '../GameResultActions';
import { canShowPassTurn } from '../../game/passTurn';

export default function GameActionsBar({
  slot,
  state,
  modeAi,
  resultText,
  actions,
}) {
  const { t } = useTranslation();

  return (
    <div
      className={[
        'game-actions-bar',
        `game-actions-bar--${slot}`,
        state.gameOver ? 'game-actions-bar--game-over' : '',
      ].filter(Boolean).join(' ')}
    >
      {state.gameOver ? (
        <>
          <p className="game-result-text game-result-text--bar">{resultText}</p>
          <GameResultActions
            modeAi={modeAi}
            onLobby={actions.goToLobby}
            onPlayAgain={actions.playAgain}
            onRematch={actions.requestRematch}
            rematchReady={state.rematchReady}
            rematchOpponentReady={state.rematchOpponentReady}
            rematchUnavailable={state.rematchUnavailable}
          />
          {!modeAi && state.rematchUnavailable && (
            <p className="game-result-hint game-result-hint--warn game-result-hint--bar">
              {t('result.rematchHint')}
            </p>
          )}
        </>
      ) : (
        <GameControls
          canPass={canShowPassTurn(state)}
          onPass={actions.skipTurn}
          onOfferDraw={actions.offerDraw}
          onAcceptDraw={actions.acceptDraw}
          onDeclineDraw={actions.declineDraw}
          onCancelGame={actions.cancelGame}
          onResignClick={actions.handleResignClick}
          resignArmed={actions.resignArmed}
          drawPending={actions.drawPending}
          drawIncoming={actions.drawIncoming}
          canCancelGame={actions.canCancelGame}
          hideDraw={modeAi}
        />
      )}
    </div>
  );
}
