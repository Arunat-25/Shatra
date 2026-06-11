import { passTurnColor } from '../game/passTurn';

export function positionLabel(num) {
  return `position${num}`;
}

export function isHintWsMessage(data) {
  return Boolean(data?.position && !data?.move_from && !data?.move_to);
}

export function buildHintPayload(positionNum) {
  return { position: positionLabel(positionNum) };
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
  const mover = passTurnColor(gameState);
  return {
    move_from: positionLabel(0),
    move_to: positionLabel(0),
    movers_color: mover,
    board: gameState.board,
    position_for_mandatory_capture: 0,
  };
}

export function buildResignPayload() {
  return { type: 'resign' };
}

export function buildOfferDrawPayload() {
  return { type: 'offer_draw' };
}

export function buildDeclineDrawPayload() {
  return { type: 'decline_draw' };
}

export function buildCancelGamePayload() {
  return { type: 'cancel_game' };
}

export function buildRequestRematchPayload() {
  return { type: 'request_rematch' };
}
