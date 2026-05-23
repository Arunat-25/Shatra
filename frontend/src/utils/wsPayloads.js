export function positionLabel(num) {
  return `position${num}`;
}

export function buildHintPayload(gameState, positionNum) {
  return {
    position: positionLabel(positionNum),
    movers_color: gameState.moversColor,
    board: gameState.board,
    position_for_mandatory_capture: gameState.posForMandatoryCapture,
  };
}

export function buildMovePayload(gameState, from, to) {
  return {
    move_from: positionLabel(from),
    move_to: positionLabel(to),
    movers_color: gameState.moversColor,
    board: gameState.board,
    position_for_mandatory_capture: gameState.posForMandatoryCapture,
  };
}

export function buildPassPayload(gameState) {
  return buildMovePayload(gameState, 0, 0);
}
