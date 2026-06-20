import { describe, expect, it } from 'vitest';
import { gameReducer, initialGameState } from './reducer';
import { GAME_ACTIONS } from './actions';

describe('gameReducer', () => {
  it('GAME_OVER locks board and stores winner_color', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.GAME_OVER,
      payload: { winner_color: 'белый', reason: 'timeout', desk: { 10: 'черный бий' } },
    });
    expect(next.gameOver).toBe(true);
    expect(next.gameOverReason).toBe('timeout');
    expect(next.winnerColor).toBe('белый');
  });

  it('GAME_CANCELLED stores message_code', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.GAME_CANCELLED,
      payload: { message_code: 'cancel.you' },
    });
    expect(next.gameOver).toBe(true);
    expect(next.gameOverReason).toBe('cancelled');
    expect(next.gameOverMessageCode).toBe('cancel.you');
    expect(next.winnerColor).toBe('');
  });

  it('OPPONENT_DISCONNECTED sets countdown', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.OPPONENT_DISCONNECTED,
      payload: { timeout: 30 },
    });
    expect(next.opponentDisconnected).toBe(true);
    expect(next.disconnectTimeout).toBe(30);
  });

  it('OPPONENT_RECONNECTED clears rematchUnavailable after finished game', () => {
    const next = gameReducer(
      {
        ...initialGameState,
        gameOver: true,
        rematchUnavailable: true,
        opponentDisconnected: true,
        disconnectCountdown: 12,
      },
      { type: GAME_ACTIONS.OPPONENT_RECONNECTED },
    );
    expect(next.rematchUnavailable).toBe(false);
    expect(next.opponentDisconnected).toBe(false);
  });

  it('SET_REMATCH_STATUS tracks both sides', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.SET_REMATCH_STATUS,
      payload: { self_ready: true, opponent_ready: true },
    });
    expect(next.rematchReady).toBe(true);
    expect(next.rematchOpponentReady).toBe(true);
  });

  it('GAME_STARTED clears waiting', () => {
    const next = gameReducer(
      { ...initialGameState, waiting: true },
      {
        type: GAME_ACTIONS.GAME_STARTED,
        payload: {
          desk: { 10: 'черный бий' },
          movers_color: 'белый',
          your_color: 'белый',
        },
      },
    );
    expect(next.waiting).toBe(false);
    expect(next.myColor).toBe('белый');
  });

  it('keeps captured pieces visible while capture chain continues', () => {
    const state = {
      ...initialGameState,
      board: {
        20: 'белая шатра',
        28: 'черная шатра',
      },
    };

    const pending = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 36: 'белая шатра' },
        captured_positions: [28],
        position_for_mandatory_capture: 36,
      },
    });

    expect(pending.capturedGhostPieces).toEqual({ 28: 'черная шатра' });
    expect(pending.moveFrom).toBe(36);

    const finished = gameReducer(pending, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 52: 'белая шатра' },
        captured_positions: [44],
        position_for_mandatory_capture: null,
      },
    });

    expect(finished.capturedGhostPieces).toEqual({});
    expect(finished.moveFrom).toBe(null);
  });

  it('MOVE_MADE applies delta-only payload without desk', () => {
    const state = {
      ...initialGameState,
      board: { 45: 'белый бий', 37: null },
      movesHistory: [],
    };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        from_pos: 45,
        to_pos: 37,
        mover: 'белый',
        movers_color: 'черный',
        message_code: 'turn.now',
        ply: 1,
      },
    });
    expect(next.board[45]).toBeNull();
    expect(next.board[37]).toBe('белый бий');
    expect(next.movesHistory).toHaveLength(1);
    expect(next.confirmedPly).toBe(1);
  });

  it('MOVE_MADE updates timer when time in payload', () => {
    const syncedAtBefore = Date.now();
    const state = {
      ...initialGameState,
      timer: { белый: 100, черный: 200 },
      timerSyncedAt: syncedAtBefore,
    };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 19: 'белый бий' },
        movers_color: 'черный',
        time: { белый: 105, черный: 200 },
      },
    });
    expect(next.timer).toEqual({ белый: 105, черный: 200 });
    expect(next.timerSyncedAt).toBeGreaterThanOrEqual(syncedAtBefore);
  });

  it('MOVE_MADE applies essential_positions from server payload', () => {
    const state = { ...initialGameState, myColor: 'белый' };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 19: 'белый бий' },
        movers_color: 'белый',
        position_for_mandatory_capture: 19,
        essential_positions: [33, 35],
        captured_pieces: [26],
      },
    });
    expect(next.moveFrom).toBe(19);
    expect(next.highlightedEssential).toEqual([33, 35]);
    expect(next.highlightedCaptured).toEqual([26]);
  });

  it('MOVE_MADE chain does not select or highlight for opponent', () => {
    const state = { ...initialGameState, myColor: 'черный' };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 19: 'белый бий' },
        movers_color: 'белый',
        position_for_mandatory_capture: 19,
        essential_positions: [33, 35],
        captured_pieces: [26],
      },
    });
    expect(next.moveFrom).toBe(null);
    expect(next.highlightedEssential).toEqual([]);
    expect(next.highlightedCaptured).toEqual([]);
  });

  it('MOVE_MADE chain step without essential clears stale highlights', () => {
    const inChain = {
      ...initialGameState,
      myColor: 'белый',
      moveFrom: 19,
      posForMandatoryCapture: 19,
      highlightedEssential: [33, 35],
      highlightedCaptured: [26],
    };
    const next = gameReducer(inChain, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 33: 'белый бий' },
        movers_color: 'белый',
        position_for_mandatory_capture: 33,
      },
    });
    expect(next.moveFrom).toBe(33);
    expect(next.highlightedEssential).toEqual([]);
    expect(next.highlightedCaptured).toEqual([]);
  });

  it('MOVE_MADE ignores stale ply', () => {
    const state = {
      ...initialGameState,
      board: { 45: 'белый бий' },
      confirmedPly: 3,
      pendingMoves: [{ ply: 4, from: 45, to: 37 }],
    };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        from_pos: 45,
        to_pos: 37,
        ply: 3,
        message_code: 'turn.now',
      },
    });
    expect(next).toBe(state);
  });

  it('OPTIMISTIC_MOVE queues pending with ply', () => {
    const state = { ...initialGameState, confirmedPly: 1, board: { 10: 'белый бий' } };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.OPTIMISTIC_MOVE,
      payload: {
        result: { updatedPositions: { 18: 'белый бий' }, moversColor: 'черный' },
        from: 10,
        to: 18,
        ply: 2,
      },
    });
    expect(next.pendingMoves).toEqual([{ from: 10, to: 18, ply: 2 }]);
    expect(next.syncStatus).toBe('pending');
  });

  it('MOVE_MADE without chain clears selection and highlights', () => {
    const inChain = gameReducer(
      { ...initialGameState, myColor: 'белый' },
      {
        type: GAME_ACTIONS.MOVE_MADE,
        payload: {
          desk: { 19: 'белый бий' },
          movers_color: 'белый',
          position_for_mandatory_capture: 19,
          essential_positions: [33],
        },
      },
    );
    const next = gameReducer(inChain, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        desk: { 33: 'белый бий' },
        position_for_mandatory_capture: null,
      },
    });
    expect(next.moveFrom).toBe(null);
    expect(next.highlightedEssential).toEqual([]);
    expect(next.highlightedCaptured).toEqual([]);
  });

  it('MOVE_MADE with stale mandatory does not leak captured ghosts on turn switch (H31)', () => {
    const state = {
      ...initialGameState,
      myColor: 'белый',
      moversColor: 'белый',
      board: { 2: 'белый батыр', 35: 'черная шатра', 42: null },
      capturedGhostPieces: { 35: 'черная шатра' },
    };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        from_pos: 2,
        to_pos: 42,
        mover: 'белый',
        movers_color: 'черный',
        captured_positions: [35],
        captured_pieces: [35],
        position_for_mandatory_capture: 42,
        ply: 1,
      },
    });
    expect(next.posForMandatoryCapture).toBeNull();
    expect(next.batyrCapturedThisTurn).toEqual([]);
    expect(next.capturedGhostPieces).toEqual({});
  });

  it('MOVE_MADE clears batyrCapturedThisTurn when turn switches', () => {
    const state = {
      ...initialGameState,
      myColor: 'белый',
      moversColor: 'белый',
      board: { 2: 'белый батыр', 35: 'черная шатра', 42: null },
      batyrCapturedThisTurn: [58, 55],
    };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        from_pos: 2,
        to_pos: 42,
        mover: 'белый',
        movers_color: 'черный',
        captured_positions: [35],
        captured_pieces: [35],
        ply: 1,
      },
    });
    expect(next.moversColor).toBe('черный');
    expect(next.batyrCapturedThisTurn).toEqual([]);
  });

  it('OPTIMISTIC_MOVE clears chain cell when turn switches', () => {
    const state = {
      ...initialGameState,
      myColor: 'белый',
      moversColor: 'белый',
      board: { 45: 'белый бий', 37: null },
    };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.OPTIMISTIC_MOVE,
      payload: {
        from: 45,
        to: 37,
        ply: 1,
        result: {
          updatedPositions: { 45: null, 37: 'белый бий' },
          moversColor: 'черный',
          positionForMandatoryCapture: 37,
          capturedPieces: [],
          capturedPositions: [],
        },
      },
    });
    expect(next.posForMandatoryCapture).toBeNull();
    expect(next.moveFrom).toBeNull();
  });

  it('MOVE_MADE clears canPass when turn switches even if payload still offers pass', () => {
    const state = {
      ...initialGameState,
      myColor: 'белый',
      moversColor: 'белый',
      canPass: true,
      posForMandatoryCapture: 19,
      board: { 19: 'белый бий' },
    };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        from_pos: 0,
        to_pos: 0,
        mover: 'белый',
        movers_color: 'черный',
        opportunity_pass_the_move: true,
        position_for_mandatory_capture: 19,
        ply: 1,
      },
    });
    expect(next.moversColor).toBe('черный');
    expect(next.canPass).toBe(false);
    expect(next.posForMandatoryCapture).toBeNull();
  });

  it('ROLLBACK_OPTIMISTIC restores canPass and batyr from snapshot', () => {
    const before = {
      ...initialGameState,
      board: { 45: 'белый бий', 37: null },
      moversColor: 'белый',
      canPass: false,
      batyrCapturedThisTurn: [],
      confirmedPly: 1,
    };
    const optimistic = gameReducer(before, {
      type: GAME_ACTIONS.OPTIMISTIC_MOVE,
      payload: {
        from: 45,
        to: 37,
        ply: 2,
        result: {
          updatedPositions: { 45: null, 37: 'белый бий' },
          moversColor: 'черный',
          opportunityPassTheMove: true,
          capturedPieces: [10],
          positionForMandatoryCapture: 37,
        },
      },
    });
    expect(optimistic.canPass).toBe(false);
    const rolled = gameReducer(optimistic, { type: GAME_ACTIONS.ROLLBACK_OPTIMISTIC });
    expect(rolled.canPass).toBe(false);
    expect(rolled.batyrCapturedThisTurn).toEqual([]);
    expect(rolled.board[45]).toBe('белый бий');
  });

  it('EXIT_HISTORY keeps live chain and batyr state (H28)', () => {
    const live = {
      ...initialGameState,
      myColor: 'белый',
      moversColor: 'черный',
      posForMandatoryCapture: 8,
      batyrCapturedThisTurn: [10],
      movesHistory: [
        { from_pos: 14, to_pos: 8, desk: { '8': 'черный батыр', '10': null, '14': null } },
      ],
      viewingHistoryIndex: 0,
      board: { 14: 'черный батыр', 10: 'белая шатра', 8: null },
    };
    const next = gameReducer(live, { type: GAME_ACTIONS.EXIT_HISTORY });
    expect(next.viewingHistoryIndex).toBeNull();
    expect(next.board[8]).toBe('черный батыр');
    expect(next.posForMandatoryCapture).toBe(8);
    expect(next.batyrCapturedThisTurn).toEqual([10]);
  });

  it('GAME_OVER clears chain highlights and ghosts (H32)', () => {
    const inChain = {
      ...initialGameState,
      posForMandatoryCapture: 19,
      batyrCapturedThisTurn: [26],
      moveFrom: 19,
      capturedGhostPieces: { 26: 'черная шатра' },
      highlightedEssential: [33],
      highlightedCaptured: [26],
      board: { 19: 'белый бий' },
    };
    const next = gameReducer(inChain, {
      type: GAME_ACTIONS.GAME_OVER,
      payload: { winner_color: 'белый', reason: 'resign', desk: inChain.board },
    });
    expect(next.gameOver).toBe(true);
    expect(next.moveFrom).toBeNull();
    expect(next.capturedGhostPieces).toEqual({});
  });

  it('GAME_STARTED restores chain and batyr state from snapshot payload', () => {
    const next = gameReducer(initialGameState, {
      type: GAME_ACTIONS.GAME_STARTED,
      payload: {
        desk: { 14: 'черный батыр', 8: null },
        movers_color: 'черный',
        your_color: 'белый',
        position_for_mandatory_capture: 8,
        captured_pieces: [10],
        ply: 3,
      },
    });
    expect(next.posForMandatoryCapture).toBe(8);
    expect(next.batyrCapturedThisTurn).toEqual([10]);
  });

  it('GAME_STARTED resync replaces stale client chain and ghost state (reconnect)', () => {
    const stale = {
      ...initialGameState,
      myColor: 'белый',
      moversColor: 'белый',
      board: { 45: 'белый бий', 28: 'черная шатра' },
      posForMandatoryCapture: 45,
      batyrCapturedThisTurn: [99],
      capturedGhostPieces: { 28: 'черная шатра' },
      moveFrom: 45,
      highlightedEssential: [33],
      confirmedPly: 1,
      waiting: false,
    };
    const next = gameReducer(stale, {
      type: GAME_ACTIONS.GAME_STARTED,
      payload: {
        desk: { 8: 'черный батыр', 10: null, 14: null },
        movers_color: 'черный',
        your_color: 'белый',
        position_for_mandatory_capture: 8,
        captured_pieces: [10],
        ply: 5,
      },
    });
    expect(next.confirmedPly).toBe(5);
    expect(next.moversColor).toBe('черный');
    expect(next.posForMandatoryCapture).toBe(8);
    expect(next.batyrCapturedThisTurn).toEqual([10]);
    expect(next.capturedGhostPieces).toEqual({});
    expect(next.moveFrom).toBeNull();
    expect(next.highlightedEssential).toEqual([]);
  });
});
