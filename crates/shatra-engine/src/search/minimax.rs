use std::time::Instant;

use crate::rules::board::Board;
use crate::rules::endgame::is_game_over;

use super::eval::{
    evaluate, evaluate_chain_potential, fortress_deploy_search_penalty,
    fortress_entry_search_adjustment, mandatory_capture_chain_bonus,
};
use super::legal::{
    is_quiescence_move, move_limit, ordered_moves, select_moves_for_search,
};
use super::state::{Move, SearchState};
use super::util::{
    child_state, get_legal_moves, is_capture_move, terminal_score, LOSE_SCORE, WIN_SCORE,
};
use super::weights::EvalWeights;
use super::{time_exceeded, MAX_QUIESCE_DEPTH, MAX_QUIESCE_TIER3_MOVES};

pub fn quiescence(
    state: &SearchState,
    mut alpha: i32,
    mut beta: i32,
    maximizing: bool,
    ai_color: &str,
    depth: i32,
    start_time: Option<Instant>,
    time_limit: f64,
    weights: &EvalWeights,
) -> i32 {
    if time_exceeded(start_time, time_limit) {
        return evaluate(&state.cells, ai_color, None, weights);
    }
    let stand = evaluate(&state.cells, ai_color, None, weights);
    if depth >= MAX_QUIESCE_DEPTH {
        return stand;
    }
    if maximizing {
        if stand >= beta {
            return beta;
        }
        alpha = alpha.max(stand);
    } else {
        if stand <= alpha {
            return alpha;
        }
        beta = beta.min(stand);
    }

    let tactical: Vec<Move> = get_legal_moves(state)
        .into_iter()
        .filter(|m| is_quiescence_move(state, *m, ai_color))
        .collect();
    if tactical.is_empty() {
        return stand;
    }

    let q_cap = move_limit(state, weights) + MAX_QUIESCE_TIER3_MOVES;
    let tactical = select_moves_for_search(
        state,
        tactical,
        ai_color,
        maximizing,
        start_time,
        time_limit,
        Some(q_cap),
        weights,
    );

    for mv in tactical {
        if time_exceeded(start_time, time_limit) {
            return stand;
        }
        let (child_opt, result) = child_state(state, mv.0, mv.1);
        let Some(child) = child_opt else { continue };

        let moving_piece = state.cells.get(&mv.0).and_then(|x| x.as_ref());
        let is_biy_move = moving_piece.map(|n| n.contains("бий")).unwrap_or(false);
        let extra_depth = if is_biy_move { 1 } else { 0 };

        let val = if let Some(terminal) = terminal_score(&result, ai_color) {
            terminal
        } else {
            let next_max = child.to_move == ai_color;
            let mandatory_chain = state.chain_cell.is_some()
                || child.chain_cell.is_some()
                || is_capture_move(
                    &state.cells,
                    &state.to_move,
                    mv.0,
                    mv.1,
                    &state.batyr_captured,
                );
            let next_depth = if mandatory_chain {
                depth + 1
            } else {
                (depth + 1 + extra_depth).min(MAX_QUIESCE_DEPTH + 2)
            };
            quiescence(
                &child,
                alpha,
                beta,
                next_max,
                ai_color,
                next_depth,
                start_time,
                time_limit,
                weights,
            )
        };

        if maximizing {
            if val >= beta {
                return beta;
            }
            alpha = alpha.max(val);
        } else {
            if val <= alpha {
                return alpha;
            }
            beta = beta.min(val);
        }
    }
    if maximizing {
        alpha
    } else {
        beta
    }
}

pub fn minimax(
    state: &SearchState,
    depth: i32,
    mut alpha: i32,
    mut beta: i32,
    maximizing: bool,
    ai_color: &str,
    start_time: Option<Instant>,
    time_limit: f64,
    weights: &EvalWeights,
) -> (i32, Option<Move>) {
    if time_exceeded(start_time, time_limit) {
        return (evaluate(&state.cells, ai_color, None, weights), None);
    }
    let end = is_game_over(&Board::new(state.cells.clone()), None, 0);
    if end.over && end.winner_color.is_some() {
        return (evaluate(&state.cells, ai_color, None, weights), None);
    }
    if depth == 0 {
        let val = quiescence(
            state,
            alpha,
            beta,
            maximizing,
            ai_color,
            0,
            start_time,
            time_limit,
            weights,
        );
        return (val, None);
    }

    let mut current_depth = depth;
    if !maximizing && state.to_move == ai_color {
        let moves = get_legal_moves(state);
        let has_chain = moves
            .iter()
            .take(5)
            .any(|m| evaluate_chain_potential(&state.cells, ai_color, *m, weights) > 0);
        if has_chain {
            current_depth = (depth + 1).min(depth + 2);
        }
    }

    let moves = ordered_moves(
        state,
        ai_color,
        maximizing,
        start_time,
        time_limit,
        weights,
    );
    if moves.is_empty() {
        return (
            if maximizing { LOSE_SCORE } else { WIN_SCORE },
            None,
        );
    }

    let mut best_move: Option<Move> = None;
    let mut best_val = if maximizing { i32::MIN } else { i32::MAX };

    if maximizing {
        for mv in moves {
            if time_exceeded(start_time, time_limit) {
                if best_move.is_some() {
                    return (best_val, best_move);
                }
                return (evaluate(&state.cells, ai_color, None, weights), None);
            }
            let (child_opt, result) = child_state(state, mv.0, mv.1);
            let Some(child) = child_opt else { continue };
            let mut val = if let Some(terminal) = terminal_score(&result, ai_color) {
                terminal
            } else {
                minimax(
                    &child,
                    current_depth - 1,
                    alpha,
                    beta,
                    child.to_move == ai_color,
                    ai_color,
                    start_time,
                    time_limit,
                    weights,
                )
                .0
            };
            if state.to_move == ai_color {
                val -= fortress_deploy_search_penalty(state, mv, ai_color, weights);
                val += mandatory_capture_chain_bonus(state, mv, ai_color, weights);
            }
            val += fortress_entry_search_adjustment(state, mv, ai_color, weights);
            if val > best_val {
                best_val = val;
                best_move = Some(mv);
            }
            alpha = alpha.max(val);
            if beta <= alpha {
                break;
            }
        }
        (best_val, best_move)
    } else {
        for mv in moves {
            if time_exceeded(start_time, time_limit) {
                if best_move.is_some() {
                    return (best_val, best_move);
                }
                return (evaluate(&state.cells, ai_color, None, weights), None);
            }
            let (child_opt, result) = child_state(state, mv.0, mv.1);
            let Some(child) = child_opt else { continue };
            let mut val = if let Some(terminal) = terminal_score(&result, ai_color) {
                terminal
            } else {
                minimax(
                    &child,
                    current_depth - 1,
                    alpha,
                    beta,
                    child.to_move == ai_color,
                    ai_color,
                    start_time,
                    time_limit,
                    weights,
                )
                .0
            };
            val += fortress_entry_search_adjustment(state, mv, ai_color, weights);
            if val < best_val {
                best_val = val;
                best_move = Some(mv);
            }
            beta = beta.min(val);
            if beta <= alpha {
                break;
            }
        }
        (best_val, best_move)
    }
}
