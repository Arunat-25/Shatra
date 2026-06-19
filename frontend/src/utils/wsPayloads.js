import { passTurnColor } from '../game/passTurn';
import { nextOutgoingPly } from '../game/syncLayer';
import {
  buildV2MovePayload,
  buildV2PassPayload,
  buildV2ResignPayload,
  buildV2OfferDrawPayload,
  buildV2DeclineDrawPayload,
  buildV2CancelGamePayload,
  buildV2RequestRematchPayload,
  buildV2ChatPayload,
  nextClientPly,
} from '../ws/v2/payloads';

export function positionLabel(num) {
  return `position${num}`;
}

export function buildMovePayload(gameState, from, to) {
  return buildV2MovePayload(from, to, nextClientPly(gameState));
}

export function buildPassPayload(gameState) {
  return buildV2PassPayload(nextClientPly(gameState));
}

export function buildResignPayload() {
  return buildV2ResignPayload();
}

export function buildOfferDrawPayload() {
  return buildV2OfferDrawPayload();
}

export function buildDeclineDrawPayload() {
  return buildV2DeclineDrawPayload();
}

export function buildCancelGamePayload() {
  return buildV2CancelGamePayload();
}

export function buildRequestRematchPayload() {
  return buildV2RequestRematchPayload();
}

export function buildChatPayload(text) {
  return buildV2ChatPayload(text);
}
