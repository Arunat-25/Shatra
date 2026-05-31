import { describe, expect, it } from 'vitest';
import { getEmptyBoard, getStartingBoard } from './startingBoard';

describe('startingBoard', () => {
  it('empty board has 62 cells', () => {
    const board = getEmptyBoard();
    expect(Object.keys(board)).toHaveLength(62);
    expect(board[1]).toBeNull();
    expect(board[62]).toBeNull();
  });

  it('starting board matches engine layout', () => {
    const board = getStartingBoard();
    expect(board[1]).toBe('черная шатра');
    expect(board[10]).toBe('черный бий');
    expect(board[53]).toBe('белый бий');
    expect(board[54]).toBe('белая шатра');
    expect(board[25]).toBeNull();
    expect(board[38]).toBeNull();
  });
});
