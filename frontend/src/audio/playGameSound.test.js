import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GAME_ACTIONS } from '../game/actions';
import { playForAction, playForServerError } from './playGameSound';

vi.mock('./soundSettings', () => ({
  getEffectiveVolume: vi.fn(() => 0.5),
}));

vi.mock('./gameSounds', () => ({
  playMove: vi.fn(),
  playCapture: vi.fn(),
  playGameStart: vi.fn(),
  playWin: vi.fn(),
  playLoss: vi.fn(),
  playDraw: vi.fn(),
  playSelect: vi.fn(),
  playError: vi.fn(),
  playChat: vi.fn(),
  playDrawOffer: vi.fn(),
}));

vi.mock('../api', () => ({
  getClientId: vi.fn(() => 'me'),
}));

import * as sounds from './gameSounds';
import { getEffectiveVolume } from './soundSettings';

describe('playGameSound', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getEffectiveVolume.mockReturnValue(0.5);
  });

  it('plays move on MOVE_MADE without captures', () => {
    playForAction(
      {
        type: GAME_ACTIONS.MOVE_MADE,
        payload: { desk: {}, from_pos: 11, to_pos: 19, movers_color: 'черный' },
      },
      { myColor: 'белый' },
      () => 'белый',
    );
    expect(sounds.playMove).toHaveBeenCalled();
    expect(sounds.playCapture).not.toHaveBeenCalled();
  });

  it('does not replay move sound when server confirms optimistic move', () => {
    playForAction(
      {
        type: GAME_ACTIONS.OPTIMISTIC_MOVE,
        payload: { result: { capturedPositions: [] }, from: 11, to: 19, ply: 1 },
      },
      { myColor: 'белый' },
      () => 'белый',
    );
    expect(sounds.playMove).toHaveBeenCalledTimes(1);

    playForAction(
      {
        type: GAME_ACTIONS.MOVE_MADE,
        payload: {
          from_pos: 11,
          to_pos: 19,
          movers_color: 'белый',
          mover: 'белый',
        },
      },
      { myColor: 'белый', pendingMove: { from: 11, to: 19, ply: 1 } },
      () => 'белый',
    );
    expect(sounds.playMove).toHaveBeenCalledTimes(1);
  });

  it('plays capture when captured_positions present', () => {
    playForAction(
      {
        type: GAME_ACTIONS.MOVE_MADE,
        payload: {
          desk: {},
          from_pos: 11,
          to_pos: 19,
          captured_positions: [19],
          movers_color: 'черный',
        },
      },
      { myColor: 'белый' },
      () => 'белый',
    );
    expect(sounds.playCapture).toHaveBeenCalled();
    expect(sounds.playMove).not.toHaveBeenCalled();
  });

  it('skips move sound for hint responses without from_pos/to_pos', () => {
    playForAction(
      {
        type: GAME_ACTIONS.MOVE_MADE,
        payload: { desk: {}, essential_positions: [19], captured_pieces: [28] },
      },
      { myColor: 'белый' },
      () => 'белый',
    );
    expect(sounds.playMove).not.toHaveBeenCalled();
    expect(sounds.playCapture).not.toHaveBeenCalled();
  });

  it('plays win when winner matches my color', () => {
    playForAction(
      {
        type: GAME_ACTIONS.GAME_OVER,
        payload: { winner_color: 'белый', game_over: true },
      },
      { myColor: 'белый' },
      () => 'белый',
    );
    expect(sounds.playWin).toHaveBeenCalled();
  });

  it('plays chat for messages from others', () => {
    playForAction(
      {
        type: GAME_ACTIONS.CHAT_MESSAGE,
        payload: { client_id: 'other', text: 'hi' },
      },
      {},
      () => 'белый',
    );
    expect(sounds.playChat).toHaveBeenCalled();
  });

  it('skips chat sound for own messages', () => {
    playForAction(
      {
        type: GAME_ACTIONS.CHAT_MESSAGE,
        payload: { client_id: 'me', text: 'hi' },
      },
      {},
      () => 'белый',
    );
    expect(sounds.playChat).not.toHaveBeenCalled();
  });

  it('skips all sounds when volume is zero', () => {
    getEffectiveVolume.mockReturnValue(0);
    playForAction({ type: GAME_ACTIONS.GAME_STARTED, payload: {} }, {}, () => null);
    playForServerError();
    expect(sounds.playGameStart).not.toHaveBeenCalled();
    expect(sounds.playError).not.toHaveBeenCalled();
  });

  it('plays error on server error helper', () => {
    playForServerError();
    expect(sounds.playError).toHaveBeenCalled();
  });

  it('skips game start sound on resync snapshot', () => {
    playForAction(
      { type: GAME_ACTIONS.GAME_STARTED, payload: { _resync: true, desk: {} } },
      {},
      () => 'белый',
    );
    expect(sounds.playGameStart).not.toHaveBeenCalled();
  });

  it('skips duplicate cancel sound after optimistic cancel (H11)', () => {
    playForAction(
      { type: GAME_ACTIONS.GAME_CANCELLED, payload: { message_code: 'cancel.you' } },
      { gameOver: true, gameOverReason: 'cancelled' },
      () => 'белый',
    );
    expect(sounds.playDraw).not.toHaveBeenCalled();
  });
});
