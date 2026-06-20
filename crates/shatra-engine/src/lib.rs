pub mod error;
pub mod rules;
pub mod search;
pub mod types;

pub use error::EngineError;
pub use types::{MoveResult, TurnInput, TurnOutput};

use rules::dict::normalize_cells;
use rules::moves::process_move;
use std::collections::HashMap;
use std::time::Instant;

/// Search best move and apply rules in one step.
pub fn compute_ai_turn(input: TurnInput) -> Result<TurnOutput, EngineError> {
    let started = Instant::now();
    let cells = normalize_cells(&input.board);
    let mut position_history: HashMap<String, i32> = input
        .position_history
        .iter()
        .map(|(k, v)| (k.clone(), *v))
        .collect();

    let (from, to) = search::best_move(
        &cells,
        &input.mover_color,
        input.depth,
        input.time_ms,
        &input.pending_batyr_captures,
        input.pending_mandatory_position,
        &position_history,
        input.moves_with_two_biys,
    )?;

    let search_ms = started.elapsed().as_millis() as i32;
    let apply_start = Instant::now();

    let applied = process_move(
        &cells,
        &input.mover_color,
        from,
        to,
        input.pending_mandatory_position,
        &input.pending_batyr_captures,
        &mut position_history,
        input.moves_with_two_biys,
    );

    let apply_ms = apply_start.elapsed().as_millis() as i32;

    let updated: HashMap<i32, String> = applied
        .updated_positions
        .as_ref()
        .map(|desk| {
            desk.iter()
                .filter_map(|(k, v)| v.as_ref().map(|s| (*k, s.clone())))
                .collect()
        })
        .unwrap_or_default();

    Ok(TurnOutput {
        result: MoveResult {
            message_code: applied.message_code,
            movers_color: applied.movers_color,
            game_over: applied.game_over,
            winner_color: applied.winner_color,
            updated_positions: updated,
            captured_positions: applied.captured_positions,
            captured_pieces: applied.captured_pieces,
            position_for_mandatory_capture: applied.position_for_mandatory_capture,
            opportunity_pass_the_move: applied.opportunity_pass_the_move,
            from_pos: from,
            to_pos: to,
        },
        depth_reached: input.depth.max(1),
        search_ms,
        apply_ms,
    })
}
