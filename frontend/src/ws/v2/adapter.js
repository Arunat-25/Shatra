import { applyMoveDelta } from './applyDelta.js';

function snapshotToV1(msg) {
  const gameOver = msg.gameOver;
  return {
    status: 'game_started',
    your_color: msg.yourColor,
    movers_color: msg.turn,
    desk: msg.board,
    move_history: (msg.moveHistory || []).map((entry, idx) => ({
      move_number: entry.ply ?? idx + 1,
      mover: entry.mover,
      from_pos: entry.from,
      to_pos: entry.to,
    })),
    time_control: msg.timeControl ?? null,
    increment: msg.increment ?? null,
    time: msg.clocks ?? null,
    players_info: msg.playersInfo,
    ply: msg.ply ?? 0,
    position_for_mandatory_capture: msg.chainCell ?? null,
    captured_pieces: msg.batyrCaptured || [],
    game_over: Boolean(gameOver),
    winner_color: gameOver?.winner || '',
    reason: gameOver?.reason || '',
    draw_offer_from: msg.drawOfferFrom ?? null,
  };
}

function moveDeltaToV1(msg, prevBoard) {
  const board = applyMoveDelta(prevBoard || {}, {
    from: msg.from,
    to: msg.to,
    captured: msg.captured,
    promoted: msg.promoted,
  });

  return {
    message_code: msg.messageCode || null,
    message_params: msg.messageParams,
    movers_color: msg.turn,
    mover: msg.mover,
    desk: board,
    from_pos: msg.from,
    to_pos: msg.to,
    captured_positions: msg.captured || [],
    captured_pieces: msg.batyrCaptured || [],
    position_for_mandatory_capture: msg.chainCell ?? null,
    opportunity_pass_the_move: msg.canPass ?? false,
    game_over: msg.gameOver ?? false,
    winner_color: msg.winner || '',
    reason: msg.reason || '',
    time: msg.clocks ?? undefined,
    ply: msg.ply,
  };
}

function waitingToV1(msg) {
  return {
    status: 'waiting',
    room_type: msg.roomType,
    show_invite_link: Boolean(msg.showInviteLink),
    players_info: msg.playersInfo,
    link: msg.link,
  };
}

/**
 * Convert v2 WS envelope to v1 shape consumed by messageHandlers.
 * @param {object} msg — raw server message
 * @param {object} [ctx] — { board } for delta application
 */
export function adaptV2ServerMessage(msg, ctx = {}) {
  if (!msg || msg.v !== 2 || !msg.t) return msg;

  switch (msg.t) {
    case 'snapshot':
      return snapshotToV1(msg);
    case 'move':
      return moveDeltaToV1(msg, ctx.board);
    case 'waiting':
      return waitingToV1(msg);
    case 'reject':
      if (msg.snapshot) {
        return {
          status: 'error',
          message_code: msg.code,
          message_params: msg.messageParams,
          _v2Resync: adaptV2ServerMessage(msg.snapshot),
        };
      }
      return { status: 'error', message_code: msg.code, message_params: msg.messageParams };
    case 'error':
      return { status: 'error', message_code: msg.code, message_params: msg.messageParams };
    case 'gameOver':
      return {
        game_over: true,
        winner_color: msg.winner || '',
        reason: msg.reason || '',
        ply: msg.ply,
      };
    case 'clock':
      return { type: 'timer_tick', time: msg.clocks };
    case 'chat':
      return {
        type: 'chat',
        from_client_id: msg.from_client_id,
        username: msg.username,
        text: msg.text,
        ts: msg.ts,
        is_anonymous: msg.is_anonymous,
        display_name: msg.display_name,
      };
    case 'chat_history':
      return { type: 'chat_history', messages: msg.messages || [] };
    case 'draw_offered':
    case 'draw_declined':
    case 'rematch_status':
    case 'rematch_cancelled':
    case 'game_cancelled':
    case 'opponent_disconnected':
    case 'opponent_reconnected':
      return { status: msg.t, ...msg };
    default:
      return msg;
  }
}

export function isV2ServerMessage(msg) {
  return Boolean(msg && msg.v === 2 && msg.t);
}
