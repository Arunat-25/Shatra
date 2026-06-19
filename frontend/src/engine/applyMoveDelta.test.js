import { describe, expect, it } from 'vitest';
import {
  applyMoveDelta,
  resolveBoardFromPayload,
  appendLocalMoveHistory,
} from './applyMoveDelta.js';

describe('resolveBoardFromPayload', () => {
  it('applies delta when desk is absent', () => {
    const board = { 45: 'белый бий', 37: null };
    const next = resolveBoardFromPayload(board, {
      from_pos: 45,
      to_pos: 37,
      captured_positions: [],
    });
    expect(next[45]).toBeNull();
    expect(next[37]).toBe('белый бий');
  });

  it('prefers full desk when provided', () => {
    const board = { 45: 'белый бий' };
    const next = resolveBoardFromPayload(board, {
      desk: { 37: 'белый бий' },
      from_pos: 45,
      to_pos: 37,
    });
    expect(next[37]).toBe('белый бий');
    expect(next[45]).toBeUndefined();
  });
});

describe('appendLocalMoveHistory', () => {
  it('appends entry with desk snapshot', () => {
    const board = { 37: 'белый бий' };
    const history = appendLocalMoveHistory([], board, {
      from_pos: 45,
      to_pos: 37,
      mover: 'белый',
    });
    expect(history).toHaveLength(1);
    expect(history[0].from_pos).toBe(45);
    expect(history[0].desk['37']).toBe('белый бий');
  });
});

describe('applyMoveDelta capture', () => {
  it('removes captured piece', () => {
    const board = { 20: 'белая шатра', 28: 'черная шатра', 36: null };
    const next = applyMoveDelta(board, { from: 20, to: 36, captured: [28] });
    expect(next[28]).toBeNull();
    expect(next[36]).toBe('белая шатра');
  });
});
