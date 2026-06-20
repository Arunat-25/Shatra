use std::collections::HashMap;

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TurnInput {
    pub board: HashMap<i32, String>,
    pub mover_color: String,
    pub depth: i32,
    pub time_ms: i32,
    pub pending_batyr_captures: Vec<i32>,
    pub pending_mandatory_position: Option<i32>,
    pub position_history: HashMap<String, i32>,
    pub moves_with_two_biys: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MoveResult {
    pub message_code: String,
    pub movers_color: Option<String>,
    pub game_over: bool,
    pub winner_color: Option<String>,
    pub updated_positions: HashMap<i32, String>,
    pub captured_positions: Vec<i32>,
    pub captured_pieces: Vec<i32>,
    pub position_for_mandatory_capture: Option<i32>,
    pub opportunity_pass_the_move: bool,
    pub from_pos: i32,
    pub to_pos: i32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TurnOutput {
    pub result: MoveResult,
    pub depth_reached: i32,
    pub search_ms: i32,
    pub apply_ms: i32,
}
