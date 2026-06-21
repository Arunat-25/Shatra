//! AI search — port of backend/ai.py minimax + evaluation.

mod eval;
mod geometry;
mod legal;
mod minimax;
mod state;
mod util;
mod weights;

use std::collections::HashMap;
use std::time::Instant;

use crate::rules::dict::Cells;
use crate::EngineError;

pub use state::{Move, SearchState};
pub use weights::{default_weights, EvalWeights};

pub const MAX_MOVES_PER_NODE: i32 = 14;
pub const MAX_QUIESCE_DEPTH: i32 = 4;
pub const MAX_QUIESCE_TIER3_MOVES: i32 = 20;

const AI_TIME_LIMITS: &[(i32, f64)] = &[(30, 0.35), (20, 0.55), (12, 0.9)];

pub(crate) fn time_exceeded(start_time: Option<Instant>, time_limit: f64) -> bool {
    start_time
        .map(|s| s.elapsed().as_secs_f64() > time_limit)
        .unwrap_or(false)
}

fn get_time_limit(_cells: &Cells, time_ms: i32) -> f64 {
    if time_ms > 0 {
        return time_ms as f64 / 1000.0;
    }
    // 0 = no artificial time cap; search runs until depth is exhausted.
    f64::MAX
}

/// Returns `(from, to)` for the chosen move.
pub fn best_move(
    cells: &Cells,
    mover: &str,
    depth: i32,
    time_ms: i32,
    batyr_caps: &[i32],
    pending: Option<i32>,
    position_history: &HashMap<String, i32>,
    _moves_with_two_biys: i32,
) -> Result<(i32, i32), EngineError> {
    if cells.is_empty() {
        return Err(EngineError::NoLegalMove);
    }

    let weights = default_weights();
    let state = SearchState::new(
        cells.clone(),
        mover,
        pending.filter(|&c| c != 0),
        batyr_caps.to_vec(),
        Some(position_history.clone()),
    );

    if let Some(chain) = pending.filter(|&c| c != 0) {
        let mut chain_state = state.clone();
        chain_state.chain_cell = Some(chain);
        if let Some(mv) = legal::pick_chain_move(&chain_state, mover, &weights) {
            return Ok(mv);
        }
        return Err(EngineError::NoLegalMove);
    }

    if let Some(win) = legal::has_obvious_win(cells, mover) {
        return Ok(win);
    }

    if let Some(win_biy) = legal::pick_winning_biy_capture(&state, mover) {
        return Ok(win_biy);
    }

    if let Some(fork) = legal::pick_best_mandatory_capture_fork(&state, mover, &weights) {
        return Ok(fork);
    }

    let mut time_limit = get_time_limit(cells, time_ms);
    let has_tactical = get_legal_moves_preview(&state, mover, &weights);
    if has_tactical {
        let tactical_cap = if time_ms > 0 {
            time_ms as f64 / 1000.0
        } else {
            f64::MAX
        };
        time_limit = (time_limit * 1.5).min(tactical_cap);
    }

    let max_depth = depth.max(1);
    let start = Instant::now();
    let mut best: Option<(i32, i32)> = None;

    for d in 1..=max_depth {
        if start.elapsed().as_secs_f64() > time_limit * 0.85 {
            break;
        }
        let (_, mv) = minimax::minimax(
            &state,
            d,
            i32::MIN,
            i32::MAX,
            true,
            mover,
            Some(start),
            time_limit,
            &weights,
        );
        if let Some(m) = mv {
            best = Some(m);
        }
    }

    if let Some(mv) = best {
        return Ok(mv);
    }

    let moves = legal::filter_moves_for_ai(
        &state,
        util::get_legal_moves(&state),
        mover,
        &weights,
    );
    if moves.is_empty() {
        return Err(EngineError::NoLegalMove);
    }

    let mut scored: Vec<(Move, i32)> = moves
        .iter()
        .map(|m| (*m, legal::move_sort_key(&state, *m, mover, &weights)))
        .collect();
    scored.sort_by_key(|(_, k)| std::cmp::Reverse(*k));
    let top_val = scored[0].1;
    let top_moves: Vec<Move> = scored
        .iter()
        .filter(|(_, k)| *k >= top_val - 50)
        .map(|(m, _)| *m)
        .collect();
    Ok(top_moves[0])
}

fn get_legal_moves_preview(state: &SearchState, ai_color: &str, weights: &EvalWeights) -> bool {
    util::get_legal_moves(state)
        .into_iter()
        .take(10)
        .any(|m| {
            eval::evaluate_chain_potential(&state.cells, ai_color, m, weights) > 0
                || eval::creates_mandatory_capture_for_opp(&state.cells, ai_color, m)
        })
}
