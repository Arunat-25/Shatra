import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { MOVE_REJECT_MESSAGE_CODES } from '@shatra/rules';
import { getEmptyBoard, getStartingBoard } from '../game/startingBoard';
import { applyLocalMove } from './localMove';
import { computeLocalHints } from './localHints';

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
    });
  }
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
