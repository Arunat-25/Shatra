export const TURN_NOW = 'turn.now';
export const MOVE_PASSED = 'move.passed';
export const MOVE_ILLEGAL = 'move.illegal';
export const MOVE_NO_PIECE = 'move.no_piece';
export const MOVE_WRONG_COLOR = 'move.wrong_color';
export const MOVE_TARGET_OCCUPIED = 'move.target_occupied';
export const MOVE_OWN_PIECE_BLOCKS = 'move.own_piece_blocks';
export const MOVE_UNKNOWN_PIECE = 'move.unknown_piece';
export const CAPTURE_CONTINUE = 'capture.continue';
export const CAPTURE_CONTINUE_SAME = 'capture.continue_same';
export const CAPTURE_MUST = 'capture.must';
export const CAPTURE_MUST_CONTINUE = 'capture.must_continue';
export const CAPTURE_MANDATORY_OTHER = 'capture.mandatory_other';
export const CAPTURE_ONLY_BIY = 'capture.only_biy';
export const PIECE_PROMOTED = 'piece.promoted';

export const VALIDATION_TO_MESSAGE = {
  NO_PIECE: MOVE_NO_PIECE,
  WRONG_COLOR: MOVE_WRONG_COLOR,
  TARGET_OCCUPIED: MOVE_TARGET_OCCUPIED,
  MANDATORY_CAPTURE_OTHER_PIECE: CAPTURE_MANDATORY_OTHER,
  ONLY_BIY_CAN_CAPTURE: CAPTURE_ONLY_BIY,
  MANDATORY_CAPTURE_THIS_PIECE: CAPTURE_MUST,
  OWN_PIECE_BLOCKS_BATYR: MOVE_OWN_PIECE_BLOCKS,
  ILLEGAL_MOVE: MOVE_ILLEGAL,
  INTERNAL_NO_PIECE: MOVE_NO_PIECE,
  OK_CAPTURE: '',
  OK_MOVE: '',
};

/** Codes that must not be applied optimistically (board unchanged or invalid). */
export const MOVE_REJECT_MESSAGE_CODES = new Set([
  MOVE_NO_PIECE,
  MOVE_WRONG_COLOR,
  MOVE_TARGET_OCCUPIED,
  MOVE_ILLEGAL,
  CAPTURE_MANDATORY_OTHER,
  CAPTURE_ONLY_BIY,
  CAPTURE_MUST,
  CAPTURE_MUST_CONTINUE,
  CAPTURE_CONTINUE_SAME,
  MOVE_UNKNOWN_PIECE,
  MOVE_OWN_PIECE_BLOCKS,
]);
