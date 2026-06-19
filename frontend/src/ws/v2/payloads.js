import { PROTO_V2 } from '../proto.js';
import { nextOutgoingPly } from '../../game/syncLayer.js';

function envelope(type, fields = {}) {
  return { v: PROTO_V2, t: type, ...fields };
}

export function buildV2MovePayload(from, to, ply) {
  return envelope('move', { from: Number(from), to: Number(to), ply: Number(ply) });
}

export function buildV2PassPayload(ply) {
  return envelope('pass', { ply: Number(ply) });
}

export function buildV2ResignPayload() {
  return envelope('resign');
}

export function buildV2OfferDrawPayload() {
  return envelope('offer_draw');
}

export function buildV2DeclineDrawPayload() {
  return envelope('decline_draw');
}

export function buildV2CancelGamePayload() {
  return envelope('cancel_game');
}

export function buildV2RequestRematchPayload() {
  return envelope('request_rematch');
}

export function buildV2ChatPayload(text) {
  return envelope('chat', { text });
}

export function buildV2SyncPayload(lastPly) {
  return envelope('sync', { lastPly: Number(lastPly) });
}

export function nextClientPly(state) {
  return nextOutgoingPly(state);
}
