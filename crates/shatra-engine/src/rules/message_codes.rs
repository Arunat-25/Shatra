pub const TURN_NOW: &str = "turn.now";
pub const MOVE_PASSED: &str = "move.passed";
pub const MOVE_ILLEGAL: &str = "move.illegal";
pub const MOVE_NO_PIECE: &str = "move.no_piece";
pub const MOVE_WRONG_COLOR: &str = "move.wrong_color";
pub const MOVE_TARGET_OCCUPIED: &str = "move.target_occupied";
pub const MOVE_OWN_PIECE_BLOCKS: &str = "move.own_piece_blocks";
pub const MOVE_UNKNOWN_PIECE: &str = "move.unknown_piece";
pub const CAPTURE_CONTINUE: &str = "capture.continue";
pub const CAPTURE_CONTINUE_SAME: &str = "capture.continue_same";
pub const CAPTURE_MUST: &str = "capture.must";
pub const CAPTURE_MUST_CONTINUE: &str = "capture.must_continue";
pub const CAPTURE_MANDATORY_OTHER: &str = "capture.mandatory_other";
pub const CAPTURE_ONLY_BIY: &str = "capture.only_biy";
pub const PIECE_PROMOTED: &str = "piece.promoted";

pub fn validation_to_message(code: &str) -> &'static str {
    match code {
        "NO_PIECE" | "INTERNAL_NO_PIECE" => MOVE_NO_PIECE,
        "WRONG_COLOR" => MOVE_WRONG_COLOR,
        "TARGET_OCCUPIED" => MOVE_TARGET_OCCUPIED,
        "MANDATORY_CAPTURE_OTHER_PIECE" => CAPTURE_MANDATORY_OTHER,
        "ONLY_BIY_CAN_CAPTURE" => CAPTURE_ONLY_BIY,
        "MANDATORY_CAPTURE_THIS_PIECE" => CAPTURE_MUST,
        "OWN_PIECE_BLOCKS_BATYR" => MOVE_OWN_PIECE_BLOCKS,
        "ILLEGAL_MOVE" => MOVE_ILLEGAL,
        _ => MOVE_ILLEGAL,
    }
}
