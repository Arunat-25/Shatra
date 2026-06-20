import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { MOVE_REJECT_MESSAGE_CODES } from '@shatra/rules';
import { getEmptyBoard, getStartingBoard } from '../game/startingBoard';
import { applyLocalMove } from './localMove';
import { computeLocalHints } from './localHints';
import { gameReducer, initialGameState } from '../game/reducer';
import { GAME_ACTIONS } from '../game/actions';
import { adaptV2ServerMessage } from '../ws/v2/adapter';

const here = dirname(fileURLToPath(import.meta.url));
const fixturePath = join(here, '../../../tests/fixtures/sync/client_server_sync.json');
const { scenarios } = JSON.parse(readFileSync(fixturePath, 'utf8'));

function emptyBoard() {
  return getEmptyBoard();
}

function initialBoardForScenario(scenario) {
  if (scenario.board) return boardFromFixture(scenario.board);
  return getStartingBoard();
}

function boardFromFixture(cells) {
  const board = emptyBoard();
  for (const [key, value] of Object.entries(cells || {})) {
    board[Number(key)] = value;
  }
  return board;
}

function gameStateFromServer({ board, mover, pending, batyrCaptured = [] }) {
  return {
    board,
    moversColor: mover,
    posForMandatoryCapture: pending ?? null,
    batyrCapturedThisTurn: batyrCaptured,
  };
}

/** Mirror backend persist_pending_mandatory_position on the client. */
function persistClientChainCell(result, prevMover) {
  const pending = result.positionForMandatoryCapture ?? null;
  if (pending != null && result.moversColor === prevMover) {
    return pending;
  }
  return null;
}

/** Mirror backend update_captures on the client replay path. */
function persistBatyrCaptures(result, prevMover, prevBatyrCaptures) {
  if (result.moversColor && result.moversColor !== prevMover) {
    return [];
  }
  if (result.capturedPieces?.length) {
    return [...result.capturedPieces];
  }
  if (!result.positionForMandatoryCapture) {
    return [];
  }
  return prevBatyrCaptures;
}

function replayWithClientRules(moves, scenario = {}) {
  let board = initialBoardForScenario(scenario);
  let mover = scenario.mover ?? moves[0]?.[0] ?? scenario.expect_mover;
  let chainCell = null;
  let batyrCaptured = [];

  for (const [color, from, to] of moves) {
    expect(mover).toBe(color);
    const prevMover = mover;
    const prevBatyr = batyrCaptured;
    const state = gameStateFromServer({ board, mover, pending: chainCell, batyrCaptured });
    const { ok, result } = applyLocalMove(state, from, to);
    expect(ok).toBe(true);
    board = result.updatedPositions;
    mover = result.moversColor ?? mover;
    chainCell = persistClientChainCell(result, prevMover);
    batyrCaptured = persistBatyrCaptures(result, prevMover, prevBatyr);
  }

  return { board, mover, chainCell, batyrCaptured };
}

/** Mirror server persist + update_captures for wire payload simulation. */
function applyServerPersist(game, result, prevMover) {
  if (result.updatedPositions) game.board = result.updatedPositions;
  const pending = result.positionForMandatoryCapture ?? null;
  if (pending != null && result.moversColor === prevMover) {
    game.chainCell = pending;
  } else {
    game.chainCell = null;
  }
  if (result.moversColor && result.moversColor !== prevMover) {
    game.batyrCaptured = [];
  } else if (result.capturedPieces?.length) {
    game.batyrCaptured = [...result.capturedPieces];
  } else if (!result.positionForMandatoryCapture) {
    game.batyrCaptured = [];
  }
  if (result.moversColor) game.mover = result.moversColor;
  game.ply = (game.ply ?? 0) + 1;
}

function shatraWasPromoted(boardBefore, result, from, to) {
  if (result.messageCode === 'piece.promoted') return true;
  const before = boardBefore[from];
  const after = result.updatedPositions?.[to];
  if (!before || !before.includes('шатра')) return false;
  return Boolean(after && after.includes('батыр'));
}

function buildWireMovePayload(game, result, prevMover, from, to, boardBefore) {
  return {
    from_pos: from,
    to_pos: to,
    mover: prevMover,
    movers_color: game.mover,
    captured_positions: result.capturedPositions || [],
    captured_pieces: [...(game.batyrCaptured || [])],
    position_for_mandatory_capture: game.chainCell,
    opportunity_pass_the_move: Boolean(result.opportunityPassTheMove),
    promoted: shatraWasPromoted(boardBefore, result, from, to),
    ply: game.ply,
    message_code: result.messageCode,
  };
}

function buildV2MoveMsg(game, result, prevMover, from, to, boardBefore) {
  return {
    v: 2,
    t: 'move',
    ply: game.ply,
    mover: prevMover,
    from,
    to,
    turn: game.mover,
    captured: result.capturedPositions || [],
    promoted: shatraWasPromoted(boardBefore, result, from, to),
    chainCell: game.chainCell,
    batyrCaptured: [...(game.batyrCaptured || [])],
    canPass: Boolean(result.opportunityPassTheMove),
    messageCode: result.messageCode || '',
  };
}

function replayThroughReducer(moves, scenario = {}) {
  let game = {
    board: initialBoardForScenario(scenario),
    mover: scenario.mover ?? moves[0]?.[0] ?? scenario.expect_mover,
    chainCell: null,
    batyrCaptured: [],
    ply: 0,
  };
  let state = { ...initialGameState, myColor: game.mover, moversColor: game.mover, board: game.board };

  for (const [color, from, to] of moves) {
    expect(game.mover).toBe(color);
    const prevMover = game.mover;
    const prevBoard = { ...game.board };
    const { ok, result } = applyLocalMove(
      gameStateFromServer({
        board: game.board,
        mover: game.mover,
        pending: game.chainCell,
        batyrCaptured: game.batyrCaptured,
      }),
      from,
      to,
    );
    expect(ok).toBe(true);
    applyServerPersist(game, result, prevMover);
    const payload = buildWireMovePayload(game, result, prevMover, from, to, prevBoard);
    state = gameReducer(state, { type: GAME_ACTIONS.MOVE_MADE, payload });
    expect(state.posForMandatoryCapture).toBe(game.chainCell);
    expect(state.batyrCapturedThisTurn).toEqual(game.batyrCaptured);
    expect(state.moversColor).toBe(game.mover);

    const v2 = buildV2MoveMsg(game, result, prevMover, from, to, prevBoard);
    const adapted = adaptV2ServerMessage(v2, { board: prevBoard });
    expect(adapted.desk).toEqual(state.board);
  }

  return { game, state };
}

describe('client/server sync fixtures', () => {
  for (const scenario of scenarios) {
    describe(scenario.id, () => {
      it('replays moves and matches expected server pending', () => {
        const { board, mover, chainCell } = replayWithClientRules(scenario.moves, scenario);

        expect(mover).toBe(scenario.expect_mover);
        const expectedPending = scenario.expect_server_pending ?? null;
        expect(chainCell).toBe(expectedPending);
      });

      it('legal moves succeed locally with server chain cell', () => {
        const { board, mover, chainCell, batyrCaptured } = replayWithClientRules(scenario.moves, scenario);

        for (const move of scenario.legal_moves || []) {
          const state = gameStateFromServer({
            board,
            mover,
            pending: chainCell,
            batyrCaptured,
          });
          const { ok, result } = applyLocalMove(state, move.from, move.to);
          expect(ok).toBe(true);
          expect(result.messageCode).toBe(move.code);
          if (move.captures) {
            expect([...(result.capturedPositions || [])].sort()).toEqual([...move.captures].sort());
          }
        }
      });

      it('stale chain cell rejects moves the server would block', () => {
        const { board, mover } = replayWithClientRules(scenario.moves, scenario);

        for (const move of scenario.illegal_with_stale_chain || []) {
          const state = gameStateFromServer({
            board,
            mover,
            pending: move.stale_chain,
          });
          const { ok, result } = applyLocalMove(state, move.from, move.to);
          expect(ok).toBe(false);
          expect(MOVE_REJECT_MESSAGE_CODES.has(result.messageCode)).toBe(true);
          expect(result.messageCode).toBe(move.code);
        }
      });

      it('illegal moves without chain are rejected like the server', () => {
        const { board, mover, chainCell, batyrCaptured } = replayWithClientRules(scenario.moves, scenario);

        for (const move of scenario.illegal_moves || []) {
          const state = gameStateFromServer({
            board,
            mover,
            pending: chainCell,
            batyrCaptured,
          });
          const { ok, result } = applyLocalMove(state, move.from, move.to);
          expect(ok).toBe(false);
          if (move.code) {
            expect(result.messageCode).toBe(move.code);
          }
        }
      });

      it('hints without stale chain show mandatory targets', () => {
        if (!scenario.legal_moves?.length) return;

        const { board, mover } = replayWithClientRules(scenario.moves, scenario);

        for (const move of scenario.legal_moves) {
          const { essential, messageCode } = computeLocalHints(
            gameStateFromServer({ board, mover, pending: null }),
            move.from,
          );
          expect(essential).toContain(move.to);
          expect(messageCode).not.toBe('capture.continue_same');
        }
      });

      it('reducer MOVE_MADE replay matches server chain and batyr state', () => {
        const { game, state } = replayThroughReducer(scenario.moves, scenario);
        expect(state.moversColor).toBe(scenario.expect_mover);
        expect(state.posForMandatoryCapture).toBe(scenario.expect_server_pending ?? null);
        expect(game.mover).toBe(scenario.expect_mover);
      });
    });
  }
});

describe('client/server sync: stale batyr hints (H19)', () => {
  it('stale batyr ghosts suppress re-capture of already-jumped cells', () => {
    const board = emptyBoard();
    board[61] = 'черный батыр';
    board[55] = 'белая шатра';

    const clean = computeLocalHints({
      board,
      moversColor: 'черный',
      myColor: 'черный',
      posForMandatoryCapture: null,
      batyrCapturedThisTurn: [],
    }, 61);

    const stale = computeLocalHints({
      board,
      moversColor: 'черный',
      myColor: 'черный',
      posForMandatoryCapture: null,
      batyrCapturedThisTurn: [55],
    }, 61);

    expect(clean.captured).toContain(55);
    expect(stale.captured).not.toContain(55);
  });
});

describe('client/server sync: local optimistic promotion (H23)', () => {
  it('applyLocalMove promotes shatra on capture before server confirms', () => {
    const board = emptyBoard();
    board[56] = 'черная шатра';
    board[58] = 'белая шатра';
    board[60] = null;

    const { ok, result } = applyLocalMove(
      gameStateFromServer({ board, mover: 'черный', pending: null }),
      56,
      60,
    );
    expect(ok).toBe(true);
    expect(result.updatedPositions[60]).toBe('черный батыр');
    expect(result.updatedPositions[58]).toBeNull();
  });
});

describe('client/server sync: pass turn reducer (H24)', () => {
  it('MOVE_MADE pass clears chain canPass and batyr', () => {
    const state = {
      ...initialGameState,
      myColor: 'белый',
      moversColor: 'белый',
      canPass: true,
      posForMandatoryCapture: 19,
      batyrCapturedThisTurn: [],
      board: { 19: 'белый бий', 13: null },
    };
    const next = gameReducer(state, {
      type: GAME_ACTIONS.MOVE_MADE,
      payload: {
        from_pos: 0,
        to_pos: 0,
        mover: 'белый',
        movers_color: 'черный',
        opportunity_pass_the_move: false,
        position_for_mandatory_capture: null,
        captured_pieces: [],
        ply: 1,
        message_code: 'move.passed',
      },
    });
    expect(next.moversColor).toBe('черный');
    expect(next.canPass).toBe(false);
    expect(next.posForMandatoryCapture).toBeNull();
    expect(next.batyrCapturedThisTurn).toEqual([]);
    expect(next.moveFrom).toBeNull();
  });
});

describe('client/server sync: capture promotion (H17)', () => {
  it('v2 adapter applies batyr when promoted flag set on capture promotion', () => {
    const board = { 56: 'черная шатра', 58: 'белая шатра', 60: null };
    const adapted = adaptV2ServerMessage(
      {
        v: 2,
        t: 'move',
        ply: 1,
        from: 56,
        to: 60,
        turn: 'белый',
        captured: [58],
        promoted: true,
        messageCode: 'turn.now',
      },
      { board },
    );
    expect(adapted.desk[60]).toBe('черный батыр');
    expect(adapted.desk[58]).toBeNull();
  });
});

describe('client/server sync: user sequence 28 specifics', () => {
  const scenario = scenarios.find((s) => s.id === 'user_sequence_28_white_mandatory');

  it('cannot land on occupied capture square 36', () => {
    const { board, mover } = replayWithClientRules(scenario.moves, scenario);
    const state = gameStateFromServer({ board, mover, pending: null });

    const { ok, result } = applyLocalMove(state, 42, 36);
    expect(ok).toBe(false);
    expect(result.messageCode).toBe('move.target_occupied');
  });

  it('wrong piece with null chain does not return continue_same', () => {
    const { board, mover } = replayWithClientRules(scenario.moves, scenario);
    const state = gameStateFromServer({ board, mover, pending: null });

    const { ok, result } = applyLocalMove(state, 32, 30);
    expect(ok).toBe(false);
    expect(result.messageCode).not.toBe('capture.continue_same');
  });
});
