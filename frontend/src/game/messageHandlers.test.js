import { describe, expect, it, vi } from 'vitest';
import { dispatchServerMessage, hintMatchesSelection } from './messageHandlers';
import { GAME_ACTIONS } from './actions';

const trackGameEventMock = vi.hoisted(() => vi.fn());

vi.mock('../observability/events', () => ({
  trackGameEvent: trackGameEventMock,
}));

function collectDispatches(payload, modeAi = false, myColor = 'белый', getSelection) {
  const calls = [];
  const dispatch = (action) => calls.push(action);
  const msg = dispatchServerMessage(
    payload,
    dispatch,
    modeAi,
    () => myColor,
    getSelection,
  );
  return { calls, msg };
}

describe('dispatchServerMessage', () => {
  it('game_over dispatches GAME_OVER', () => {
    trackGameEventMock.mockClear();
    const { calls } = collectDispatches({
      game_over: true,
      winner_color: 'белый',
      reason: 'resign',
    });
    expect(calls.some((c) => c.type === GAME_ACTIONS.GAME_OVER)).toBe(true);
    expect(trackGameEventMock).toHaveBeenCalledWith(
      'game_over',
      expect.objectContaining({ reason: 'resign', winnerColor: 'белый' }),
    );
  });

  it('timer_tick updates clocks', () => {
    const { calls } = collectDispatches({
      type: 'timer_tick',
      time: { белый: 60, черный: 55 },
    });
    expect(calls).toEqual([
      { type: GAME_ACTIONS.TIMER_TICK, payload: { белый: 60, черный: 55 } },
    ]);
  });

  it('rematch_status sets ready flags', () => {
    const { calls } = collectDispatches({
      status: 'rematch_status',
      self_ready: true,
      opponent_ready: false,
    });
    expect(calls[0].type).toBe(GAME_ACTIONS.SET_REMATCH_STATUS);
    expect(calls[0].payload.opponent_ready).toBe(false);
  });

  it('rematch_cancelled marks unavailable', () => {
    const { calls } = collectDispatches({
      status: 'rematch_cancelled',
      message_code: 'rematch.opponent_left',
    });
    expect(calls[0].type).toBe(GAME_ACTIONS.SET_REMATCH_UNAVAILABLE);
  });

  it('game_cancelled ends game with message_code for result bar', () => {
    const { calls, msg } = collectDispatches({
      status: 'game_cancelled',
      message_code: 'cancel.opponent',
      by: 'белый',
    });
    expect(calls[0]).toEqual({
      type: GAME_ACTIONS.GAME_CANCELLED,
      payload: { message_code: 'cancel.opponent', message_params: undefined },
    });
    expect(msg).toBeNull();
  });

  it('game_over with cancelled reason stores message_code', () => {
    const { calls, msg } = collectDispatches({
      game_over: true,
      message_code: 'cancel.opponent',
      reason: 'cancelled',
      desk: { '10': 'белый бий' },
    });
    expect(calls.some((c) => c.type === GAME_ACTIONS.GAME_OVER)).toBe(true);
    const over = calls.find((c) => c.type === GAME_ACTIONS.GAME_OVER);
    expect(over.payload.reason).toBe('cancelled');
    expect(over.payload.message_code).toBe('cancel.opponent');
    expect(msg).toBeNull();
  });

  it('move in AI mode sets aiThinking when not my turn', () => {
    const { calls } = collectDispatches(
      {
        message_code: 'turn.now',
        desk: { '10': 'черный бий' },
        movers_color: 'черный',
        game_over: false,
      },
      true,
      'белый',
    );
    const move = calls.find((c) => c.type === GAME_ACTIONS.MOVE_MADE);
    expect(move.payload.aiThinking).toBe(true);
  });

  it('capture continue dispatches highlights when essential_positions included', () => {
    const { calls } = collectDispatches({
      message_code: 'capture.continue',
      desk: { '19': 'белый бий' },
      movers_color: 'белый',
      position_for_mandatory_capture: 19,
      essential_positions: [33],
      captured_pieces: [26],
      game_over: false,
    });
    expect(calls.some((c) => c.type === GAME_ACTIONS.MOVE_MADE)).toBe(true);
    expect(calls).toContainEqual({
      type: GAME_ACTIONS.HIGHLIGHTS,
      payload: { essential: [33], captured: [26] },
    });
  });

  it('capture continue does not dispatch highlights to opponent', () => {
    const { calls } = collectDispatches(
      {
        message_code: 'capture.continue',
        desk: { '19': 'белый бий' },
        movers_color: 'белый',
        position_for_mandatory_capture: 19,
        essential_positions: [33],
        captured_pieces: [26],
        game_over: false,
      },
      false,
      'черный',
    );
    expect(calls.some((c) => c.type === GAME_ACTIONS.HIGHLIGHTS)).toBe(false);
  });

  it('hint-only message does not dispatch highlights to opponent', () => {
    const { calls } = collectDispatches(
      {
        essential_positions: [33, 35],
        movers_color: 'белый',
      },
      false,
      'черный',
    );
    expect(calls.some((c) => c.type === GAME_ACTIONS.HIGHLIGHTS)).toBe(false);
  });

  it('ignores stale hint when hint_position does not match selection', () => {
    const { calls } = collectDispatches(
      {
        essential_positions: [33, 35],
        movers_color: 'белый',
        hint_position: 48,
      },
      false,
      'белый',
      () => ({ moveFrom: 53, chainCell: null }),
    );
    expect(calls.some((c) => c.type === GAME_ACTIONS.HIGHLIGHTS)).toBe(false);
  });

  it('applies hint when hint_position matches selection', () => {
    const { calls } = collectDispatches(
      {
        essential_positions: [33, 35],
        movers_color: 'белый',
        hint_position: 53,
      },
      false,
      'белый',
      () => ({ moveFrom: 53, chainCell: null }),
    );
    expect(calls).toContainEqual({
      type: GAME_ACTIONS.HIGHLIGHTS,
      payload: { essential: [33, 35], captured: [] },
    });
  });

  it('hintMatchesSelection allows legacy responses without hint_position', () => {
    expect(hintMatchesSelection({ essential_positions: [] }, () => ({ moveFrom: 53, chainCell: null }))).toBe(true);
  });

  it('hint-only with empty essential still updates highlights for my color', () => {
    const { calls } = collectDispatches(
      {
        essential_positions: [],
        movers_color: 'белый',
        hint_position: 53,
      },
      false,
      'белый',
      () => ({ moveFrom: 53, chainCell: null }),
    );
    expect(calls).toContainEqual({
      type: GAME_ACTIONS.HIGHLIGHTS,
      payload: { essential: [], captured: [] },
    });
  });

  it('hint-only uses chainCell when matching hint_position', () => {
    const { calls } = collectDispatches(
      {
        essential_positions: [33],
        movers_color: 'белый',
        hint_position: 19,
      },
      false,
      'белый',
      () => ({ moveFrom: null, chainCell: 19 }),
    );
    expect(calls).toContainEqual({
      type: GAME_ACTIONS.HIGHLIGHTS,
      payload: { essential: [33], captured: [] },
    });
  });

  it('server error returns localized text from message_code', () => {
    const { msg } = collectDispatches({ status: 'error', message_code: 'move.impossible' });
    expect(msg.type).toBe('error');
    expect(msg.text).toBe('Ход невозможен');
  });

  it('waiting sets players_info', () => {
    const players = [
      { client_id: 'a', display_name: 'Аноним', is_anonymous: true },
      { client_id: 'b', display_name: '@hero', is_anonymous: false },
    ];
    const { calls } = collectDispatches({
      status: 'waiting',
      players_info: players,
    });
    expect(calls.some((c) => c.type === GAME_ACTIONS.SET_WAITING)).toBe(true);
    expect(calls.some(
      (c) => c.type === GAME_ACTIONS.SET_PLAYERS_INFO && c.payload === players,
    )).toBe(true);
  });

  it('waiting sets room meta for private host invite', () => {
    const { calls } = collectDispatches({
      status: 'waiting',
      room_type: 'private',
      show_invite_link: true,
    });
    expect(calls.some(
      (c) => c.type === GAME_ACTIONS.SET_WAITING_META
        && c.payload.roomType === 'private'
        && c.payload.showInviteLink === true,
    )).toBe(true);
  });

  it('waiting without show_invite_link for guest', () => {
    const { calls } = collectDispatches({
      status: 'waiting',
      room_type: 'private',
      show_invite_link: false,
    });
    const meta = calls.find((c) => c.type === GAME_ACTIONS.SET_WAITING_META);
    expect(meta.payload.showInviteLink).toBe(false);
  });

  it('chat_history loads messages', () => {
    const messages = [{ text: 'hi', ts: 1 }];
    const { calls } = collectDispatches({ type: 'chat_history', messages });
    expect(calls[0]).toEqual({
      type: GAME_ACTIONS.CHAT_HISTORY,
      payload: messages,
    });
  });

  it('opponent_disconnected dispatches without toast message', () => {
    const { calls, msg } = collectDispatches({
      status: 'opponent_disconnected',
      timeout: 30,
    });
    expect(calls.some((c) => c.type === GAME_ACTIONS.OPPONENT_DISCONNECTED)).toBe(true);
    expect(msg).toBeNull();
  });

  it('chat appends message', () => {
    const { calls } = collectDispatches({
      type: 'chat',
      from_client_id: 'x',
      text: 'gg',
      display_name: 'player',
    });
    expect(calls[0].type).toBe(GAME_ACTIONS.CHAT_MESSAGE);
    expect(calls[0].payload.text).toBe('gg');
  });

  it('game_started includes players_info dispatch', () => {
    trackGameEventMock.mockClear();
    const info = [{ client_id: 'c1', display_name: 'u' }];
    const { calls } = collectDispatches({
      status: 'game_started',
      desk: { '10': 'белый бий' },
      movers_color: 'белый',
      your_color: 'белый',
      players_info: info,
    });
    expect(calls.some(
      (c) => c.type === GAME_ACTIONS.SET_PLAYERS_INFO && c.payload === info,
    )).toBe(true);
    expect(trackGameEventMock).toHaveBeenCalledWith(
      'game_started',
      expect.objectContaining({ moversColor: 'белый' }),
    );
  });

  it('rating_update sets players_info', () => {
    const players = [{ client_id: 'a', rating: 1210, rating_delta: 10 }];
    const { calls } = collectDispatches({
      type: 'rating_update',
      players_info: players,
    });
    expect(calls).toContainEqual({
      type: GAME_ACTIONS.SET_PLAYERS_INFO,
      payload: players,
    });
  });
});
