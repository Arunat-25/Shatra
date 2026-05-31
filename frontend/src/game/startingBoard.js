/** Mirrors backend/board_utils.py get_starting_board(). */

export function getEmptyBoard() {
  const board = {};
  for (let i = 1; i <= 62; i += 1) {
    board[i] = null;
  }
  return board;
}

export function getStartingBoard() {
  const board = getEmptyBoard();
  for (let i = 1; i <= 9; i += 1) {
    board[i] = 'черная шатра';
  }
  board[10] = 'черный бий';
  for (let i = 11; i <= 24; i += 1) {
    board[i] = 'черная шатра';
  }
  for (let i = 54; i <= 62; i += 1) {
    board[i] = 'белая шатра';
  }
  board[53] = 'белый бий';
  for (let i = 39; i <= 52; i += 1) {
    board[i] = 'белая шатра';
  }
  return board;
}
