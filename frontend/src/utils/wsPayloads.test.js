import { describe, expect, it } from 'vitest';
import { buildMovePayload, buildPassPayload } from './wsPayloads';

describe('wsPayloads v2', () => {
  it('buildMovePayload sends v2 move envelope with ply', () => {
    const payload = buildMovePayload(
      { confirmedPly: 2, pendingMoves: [] },
      45,
      37,
    );
    expect(payload).toEqual({
      v: 2,
      t: 'move',
      from: 45,
      to: 37,
      ply: 3,
    });
  });

  it('buildPassPayload sends v2 pass envelope', () => {
    const payload = buildPassPayload({ confirmedPly: 1, pendingMoves: [] });
    expect(payload).toEqual({
      v: 2,
      t: 'pass',
      ply: 2,
    });
  });
});
