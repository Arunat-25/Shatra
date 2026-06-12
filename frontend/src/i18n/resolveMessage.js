import i18n from './index';

/** Maps stable server message codes to locale keys. */
const CODE_TO_I18N = {
  // Engine / moves
  'turn.now': 'server.nowTurn',
  'move.passed': 'server.movePassed',
  'move.illegal': 'server.impossibleMove',
  'move.impossible': 'server.impossibleMove',
  'move.no_piece': 'server.impossibleMove',
  'move.wrong_color': 'server.impossibleMove',
  'move.target_occupied': 'server.impossibleMove',
  'move.own_piece_blocks': 'server.impossibleMove',
  'move.unknown_piece': 'server.impossibleMove',
  'move.invalid_event': 'server.error',
  'move.no_capture_target': 'server.impossibleMove',
  'capture.continue': 'server.continueCapture',
  'capture.continue_same': 'server.continueSamePiece',
  'capture.must': 'server.mustCapture',
  'capture.must_continue': 'server.mustCaptureContinue',
  'capture.mandatory_other': 'server.mustCapture',
  'capture.only_biy': 'server.mustCapture',
  'piece.promoted': 'server.promotion',
  'game.draw': 'result.draw',
  'draw_two_biys': 'result.drawAgreed',
  'draw_repetition': 'result.drawAgreed',

  // Control / draw / rematch / cancel
  'draw.bot_declined': 'server.drawBotDeclined',
  'draw.already_offered': 'server.drawAlreadyOffered',
  'draw.you_offered': 'server.drawYouOffered',
  'draw.opponent_offers': 'server.drawOpponentOffers',
  'draw.opponent_declined': 'server.drawOpponentDeclined',
  'draw.offer_cancelled': 'server.drawOfferCancelled',
  'draw.declined': 'server.drawDeclined',
  'draw.agreed': 'server.drawAgreed',
  'rematch.wait_self': 'server.rematchWaitSelf',
  'rematch.wait_opponent': 'server.rematchWaitOpponent',
  'rematch.opponent_left': 'server.rematchOpponentLeft',
  'rematch.cancelled': 'server.rematchCancelled',
  'cancel.you': 'server.cancelYou',
  'cancel.opponent': 'server.cancelOpponent',
  'cancel.color_unknown': 'errors.genericHttp',
  'cancel.too_late': 'server.error',

  // Chat
  'chat.ai_unavailable': 'chat.errors.aiUnavailable',
  'chat.empty': 'chat.errors.empty',
  'chat.rate_limit': 'chat.errors.rateLimit',
  'chat.too_fast': 'chat.errors.tooFast',
  'chat.duplicate': 'chat.errors.duplicate',

  // Room / WS / auth (codes match backend/message_codes.py)
  'room.not_found': 'errors.roomNotFound',
  'room.full': 'errors.roomFull',
  'room.game_started': 'errors.roomFull',
  'room.already_in_game': 'errors.alreadyInGame',
  'room_closed': 'errors.roomNotFound',
  'auth.auth_required': 'auth.authRequired',
  'auth.invalid_token': 'auth.invalidToken',
  'auth.user_not_found': 'auth.userNotFound',
  'auth.invalid_credentials': 'auth.invalidCredentials',
  'auth.session_expired': 'auth.sessionExpired',
  'auth.wrong_password': 'auth.wrongPassword',
  'auth.username_taken_register': 'auth.usernameTakenRegister',
  'auth.username_taken_profile': 'auth.usernameTakenProfile',

  // Bug reports
  'bug_report.description_too_short': 'bugReport.descriptionTooShort',
  'bug_report.description_too_long': 'bugReport.descriptionTooLong',
  'bug_report.invalid_screenshot': 'bugReport.invalidScreenshotServer',
  'bug_report.screenshot_too_large': 'bugReport.tooLarge',
  'bug_report.rate_limit': 'bugReport.rateLimit',

  // WS protocol
  'ws.invalid_json': 'errors.malformedMessage',
  'ws.expected_object': 'errors.malformedMessage',
  'ws.unknown_command': 'errors.malformedMessage',
  'ws.unknown_message': 'errors.malformedMessage',
  'ws.invalid_move_data': 'errors.malformedMessage',
  'ws.missing_board': 'errors.malformedMessage',
  'ws.missing_mover': 'errors.malformedMessage',
  'ws.game_over': 'server.error',
  'ws.not_your_turn': 'game.notYourTurn',
  'ai.no_move': 'server.error',

  // WS close reason codes
  room_not_found: 'errors.roomNotFound',
  room_full: 'errors.roomFull',
  already_in_game: 'errors.alreadyInGame',
  connection_lost: 'errors.connectionLost',
  reconnect_failed: 'errors.reconnectFailed',
};

function normalizeColorToken(raw) {
  if (!raw) return raw;
  const c = String(raw).toLowerCase();
  if (c.includes('бел')) return i18n.t('colors.white');
  if (c.includes('чер') || c.includes('чёр')) return i18n.t('colors.black');
  return raw;
}

function normalizeParams(params) {
  if (!params || typeof params !== 'object') return {};
  const out = { ...params };
  if (out.color) out.color = normalizeColorToken(out.color);
  return out;
}

export function resolveMessageCode(code, params) {
  if (!code) return '';
  const key = CODE_TO_I18N[code] || code;
  return i18n.t(key, normalizeParams(params));
}

/** Resolve from WS/API payload or plain code string. */
export function resolveMessage(input) {
  if (!input) return '';
  if (typeof input === 'string') {
    return resolveMessageCode(input);
  }
  const code = input.message_code || input.code || input.detail;
  if (!code) return '';
  return resolveMessageCode(code, input.message_params || input.params);
}

export function resolveWsErrorMessage(messageOrCode) {
  if (!messageOrCode) return messageOrCode;
  return resolveMessageCode(messageOrCode) || messageOrCode;
}

export function resolveApiErrorMessage(messageOrCode) {
  return resolveWsErrorMessage(messageOrCode);
}

/** @deprecated use resolveMessage */
export function translateServerMessage(message) {
  return resolveMessage(message);
}

/** @deprecated use resolveWsErrorMessage */
export function translateWsErrorMessage(message) {
  return resolveWsErrorMessage(message);
}

/** @deprecated use resolveApiErrorMessage */
export function translateApiErrorMessage(message) {
  return resolveApiErrorMessage(message);
}

export { CODE_TO_I18N };
