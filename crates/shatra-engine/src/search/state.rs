use std::collections::HashMap;

use crate::rules::dict::Cells;

#[derive(Debug, Clone)]
pub struct SearchState {
    pub cells: Cells,
    pub to_move: String,
    pub chain_cell: Option<i32>,
    pub batyr_captured: Vec<i32>,
    pub position_history: Option<HashMap<String, i32>>,
}

impl SearchState {
    pub fn new(
        cells: Cells,
        to_move: &str,
        chain_cell: Option<i32>,
        batyr_captured: Vec<i32>,
        position_history: Option<HashMap<String, i32>>,
    ) -> Self {
        Self {
            cells,
            to_move: to_move.to_string(),
            chain_cell,
            batyr_captured,
            position_history,
        }
    }
}

pub type Move = (i32, i32);
