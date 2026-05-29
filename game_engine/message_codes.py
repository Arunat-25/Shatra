"""Stable message codes for game engine results (UI text lives on the client)."""

# Turn / move flow
TURN_NOW = "turn.now"
MOVE_PASSED = "move.passed"
MOVE_ILLEGAL = "move.illegal"
MOVE_NO_PIECE = "move.no_piece"
MOVE_WRONG_COLOR = "move.wrong_color"
MOVE_TARGET_OCCUPIED = "move.target_occupied"
MOVE_OWN_PIECE_BLOCKS = "move.own_piece_blocks"
MOVE_UNKNOWN_PIECE = "move.unknown_piece"
MOVE_INVALID_EVENT = "move.invalid_event"
MOVE_NO_CAPTURE_TARGET = "move.no_capture_target"

# Capture chain
CAPTURE_CONTINUE = "capture.continue"
CAPTURE_CONTINUE_SAME = "capture.continue_same"
CAPTURE_MUST = "capture.must"
CAPTURE_MUST_CONTINUE = "capture.must_continue"
CAPTURE_MANDATORY_OTHER = "capture.mandatory_other"
CAPTURE_ONLY_BIY = "capture.only_biy"

# Promotion / endgame
PIECE_PROMOTED = "piece.promoted"
GAME_DRAW = "game.draw"

# Validation code -> message code
VALIDATION_TO_MESSAGE = {
    "NO_PIECE": MOVE_NO_PIECE,
    "WRONG_COLOR": MOVE_WRONG_COLOR,
    "TARGET_OCCUPIED": MOVE_TARGET_OCCUPIED,
    "MANDATORY_CAPTURE_OTHER_PIECE": CAPTURE_MANDATORY_OTHER,
    "ONLY_BIY_CAN_CAPTURE": CAPTURE_ONLY_BIY,
    "MANDATORY_CAPTURE_THIS_PIECE": CAPTURE_MUST,
    "OWN_PIECE_BLOCKS_BATYR": MOVE_OWN_PIECE_BLOCKS,
    "ILLEGAL_MOVE": MOVE_ILLEGAL,
    "INTERNAL_NO_PIECE": MOVE_NO_PIECE,
    "OK_CAPTURE": "",
    "OK_MOVE": "",
}

# Draw reasons (stored in game.reason)
DRAW_TWO_BIYS = "draw_two_biys"
DRAW_REPETITION = "draw_repetition"
