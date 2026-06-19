import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { getHints, processMove } from './src/index.js';
import { normalizeCells } from './src/board.js';

const here = dirname(fileURLToPath(import.meta.url));
const contractPath = join(here, '../../../tests/fixtures/rules/contract.json');
const contract = JSON.parse(readFileSync(contractPath, 'utf8'));

function runHintCase(action) {
  const cells = normalizeCells(action.board);
  return getHints({
    cells,
    currentColor: action.mover_color,
    fromCell: action.from_cell,
    batyrCapturedThisTurn: action.batyr_captured_this_turn || [],
    chainCaptureCell: action.chain_capture_cell ?? null,
  });
}

function runMoveCase(action) {
  const cells = normalizeCells(action.board);
  return processMove({
    cells,
    currentColor: action.mover_color,
    fromCell: action.from_cell,
    toCell: action.to_cell,
    chainCaptureCell: action.chain_capture_cell ?? null,
    batyrCapturedThisTurn: action.batyr_captured_this_turn || [],
  });
}

describe('rules contract suite', () => {
  for (const testCase of contract.cases) {
    it(testCase.id, () => {
      const { action, expect: expected } = testCase;

      if (action.type === 'hints') {
        const result = runHintCase(action);
        expect([...result.essentialPositions].sort((a, b) => a - b)).toEqual(
          expected.essential_positions,
        );
        expect(result.messageCode || '').toBe(expected.message_code || '');
        if (expected.captured_pieces != null) {
          expect(result.capturedPieces).toEqual(expected.captured_pieces);
        }
        return;
      }

      if (action.type === 'move') {
        const result = runMoveCase(action);
        expect(result.messageCode || '').toBe(expected.message_code || '');
        expect(result.moversColor).toBe(expected.movers_color);
        expect(result.positionForMandatoryCapture).toBe(
          expected.position_for_mandatory_capture,
        );
        expect([...(result.capturedPositions || [])].sort((a, b) => a - b)).toEqual(
          expected.captured_positions,
        );
        expect(result.capturedPieces || []).toEqual(expected.captured_pieces);
        expect(!!result.opportunityPassTheMove).toBe(
          expected.opportunity_pass_the_move,
        );
        if (expected.desk) {
          const desk = Object.fromEntries(
            Object.entries(result.updatedPositions || {}).map(([k, v]) => [String(k), v]),
          );
          expect(desk).toEqual(expected.desk);
        }
      }
    });
  }
});
