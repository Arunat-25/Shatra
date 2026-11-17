use std::collections::HashSet;

use crate::rules::board::Board;
use crate::rules::hints::get_all_mandatory_captures;

use crate::rules::hints::find_captured_enemy;

use super::eval::{
    biy_capture_net_if_recaptured, creates_mandatory_capture_for_opp, evaluate,
    evaluate_chain_potential, evaluate_hanging_sacrifice, fortress_deploy_justified,
    fortress_deploy_penalty_applies, fortress_entry_piece_bonus, mandatory_capture_chain_bonus,
    move_exposes_biy,
};
use super::weights::EvalWeights;
use super::geometry::{
    batyr_anchor_cells, biy_anchor_cells, biy_anchor_factor, in_danger_zone, in_side_file,
    is_biy_deploy_to_main_field, is_fortress_entry, is_fortress_shatra_deploy, main_field_density,
    piece_color_from_name, safe_piece_type,
};
use super::state::{Move, SearchState};
use super::util::{
    captured_enemy_type, child_state, get_legal_moves, get_strict_mandatory_captures,
    is_capture_move, is_cell_capturable, mandatory_moves_set, opponent_color,
    shatra_promotion_progress, terminal_score, we_won, BLACK_PROMOTION, HANGING_WITHOUT_GAIN_PENALTY,
    WHITE_PROMOTION, WIN_SCORE,
};
use super::weights::default_weights;

pub fn repetition_move_adjustment(
    state: &SearchState,
    _mv: Move,
    ai_color: &str,
    child_cells: &crate::rules::dict::Cells,
    weights: &EvalWeights,
) -> i32 {
    let Some(hist) = &state.position_history else {
        return 0;
    };
    if state.to_move != ai_color {
        return 0;
    }
    let mut entries: Vec<(i32, Option<String>)> =
        child_cells.iter().map(|(k, v)| (*k, v.clone())).collect();
    entries.sort_by_key(|(k, _)| *k);
    let key = format!("{entries:?}");
    let seen = hist.get(&key).copied().unwrap_or(0);
    if seen < 1 {
        return 0;
    }
    let material = evaluate(child_cells, ai_color, None, weights);
    if material > 400 {
        return -120_000;
    }
    if material < -400 {
        return 12_000;
    }
    -20_000
}

pub fn move_sort_key(
    state: &SearchState,
    mv: Move,
    ai_color: &str,
    weights: &EvalWeights,
) -> i32 {
    let (fm, to) = mv;
    let piece = state.cells.get(&fm).and_then(|x| x.as_ref());
    let Some(piece) = piece else {
        return -10_000;
    };
    let ptype = safe_piece_type(piece);
    let mut score = 0;

    let (child_opt, result) = child_state(state, fm, to);
    let Some(child) = child_opt else {
        return -10_000;
    };

    if let Some(terminal) = terminal_score(&result, ai_color) {
        return terminal;
    }

    if move_exposes_biy(state, mv, ai_color) {
        return -300_000;
    }

    if ptype == "бий" && state.to_move == ai_color {
        if let Some(biy_net) = biy_capture_net_if_recaptured(state, mv, ai_color, weights) {
            if biy_net < 0 {
                return -950_000;
            }
            if biy_net >= WIN_SCORE / 2 {
                return biy_net;
            }
        }
    }

    let captured = captured_enemy_type(
        &state.cells,
        &state.to_move,
        fm,
        to,
        &state.batyr_captured,
    );
    if captured.as_deref() == Some("бий") && state.to_move == ai_color {
        score += 200_000;
    } else if captured.as_deref() == Some("батыр") {
        score += 8_000;
    } else if captured.as_deref() == Some("шатра") {
        score += 2_500;
    } else if is_capture_move(&state.cells, &state.to_move, fm, to, &state.batyr_captured) {
        score += 1_200;
    }

    if ptype == "шатра" && state.to_move == ai_color {
        let promo = if ai_color == "белый" {
            WHITE_PROMOTION
        } else {
            BLACK_PROMOTION
        };
        if promo.contains(&to) {
            score += weights.promotion_bonus * 2;
        }
        score += shatra_promotion_progress(ai_color, to) * 2;
    }

    if ptype == "бий" && state.to_move == ai_color {
        if is_cell_capturable(&child.cells, &opponent_color(ai_color), to, &child.batyr_captured)
        {
            return -950_000;
        }
    }

    if state.to_move == ai_color {
        if creates_mandatory_capture_for_opp(&state.cells, ai_color, mv) {
            score -= 50_000;
        }
        score += evaluate_chain_potential(&state.cells, ai_color, mv, weights) / 2;
        score += mandatory_capture_chain_bonus(state, mv, ai_color, weights);
        let sac = evaluate_hanging_sacrifice(state, mv, ai_color, weights);
        if sac <= -HANGING_WITHOUT_GAIN_PENALTY / 2 {
            return sac;
        }
        if sac > 0 {
            score += sac;
        } else if is_cell_capturable(&child.cells, &opponent_color(ai_color), to, &child.batyr_captured)
            && !(child.chain_cell.is_some() && child.to_move == ai_color)
        {
            return -HANGING_WITHOUT_GAIN_PENALTY;
        }
        let k = biy_anchor_factor(
            main_field_density(&state.cells),
            weights.crowded_main_field_threshold,
        );
        let opp_mass = super::util::opponent_has_mass(&state.cells, ai_color);
        if opp_mass && ptype == "шатра" && in_side_file(to)
            && !is_cell_capturable(&child.cells, &opponent_color(ai_color), to, &child.batyr_captured)
        {
            score += weights.side_file_shatra_bonus;
        } else if ptype == "батыр"
            && batyr_anchor_cells(ai_color).contains(&to)
            && !is_cell_capturable(&child.cells, &opponent_color(ai_color), to, &child.batyr_captured)
        {
            score += weights.batyr_anchor_bonus;
        } else if opp_mass
            && ptype == "батыр"
            && in_side_file(to)
            && !is_cell_capturable(&child.cells, &opponent_color(ai_color), to, &child.batyr_captured)
        {
            score += weights.side_file_batyr_bonus;
        } else if ptype == "бий" && biy_anchor_cells(ai_color).contains(&to) {
            if !(main_field_density(&state.cells) >= weights.crowded_main_field_threshold
                && is_biy_deploy_to_main_field(fm, to, ai_color))
            {
                score += (weights.biy_anchor_bonus as f64 * k) as i32;
            }
        }
        if opp_mass && in_danger_zone(to) {
            score -= weights.danger_zone_penalty;
        }
        if ptype == "шатра" && is_fortress_entry(fm, to, ai_color) {
            score += fortress_entry_piece_bonus(piece, weights);
        }
        if ptype == "шатра"
            && is_fortress_shatra_deploy(fm, to, ai_color)
            && fortress_deploy_penalty_applies(&state.cells, ai_color)
            && !fortress_deploy_justified(state, mv, ai_color, weights)
        {
            score -= weights.fortress_deploy_penalty;
        }
        score += repetition_move_adjustment(state, mv, ai_color, &child.cells, weights);
    }

    score
}

pub fn filter_moves_for_ai(
    state: &SearchState,
    moves: Vec<Move>,
    ai_color: &str,
    weights: &EvalWeights,
) -> Vec<Move> {
    if state.to_move != ai_color {
        return moves;
    }
    let mut safe = Vec::new();
    for mv in &moves {
        if super::eval::is_deprioritized_move(state, *mv, ai_color, weights) {
            continue;
        }
        let (child_opt, result) = child_state(state, mv.0, mv.1);
        let Some(child) = child_opt else { continue };
        if result.game_over && we_won(&result, ai_color) {
            safe.push(*mv);
            continue;
        }
        if move_exposes_biy(state, *mv, ai_color) {
            continue;
        }
        let piece = state.cells.get(&mv.0).and_then(|x| x.as_ref());
        if piece.map(|p| safe_piece_type(p) == "бий").unwrap_or(false) {
            if let Some(biy_net) = biy_capture_net_if_recaptured(state, *mv, ai_color, weights) {
                if biy_net < 0 {
                    continue;
                }
            }
        }
        let own_chain = child.chain_cell.is_some() && child.to_move == ai_color;
        if is_cell_capturable(&child.cells, &opponent_color(ai_color), mv.1, &child.batyr_captured)
            && !own_chain
            && evaluate_hanging_sacrifice(state, *mv, ai_color, weights) <= 0
        {
            continue;
        }
        if creates_mandatory_capture_for_opp(&state.cells, ai_color, *mv)
            && evaluate_hanging_sacrifice(state, *mv, ai_color, weights) <= 0
        {
            continue;
        }
        safe.push(*mv);
    }
    if !safe.is_empty() {
        return safe;
    }
    let mut ranked = moves;
    ranked.sort_by_key(|m| std::cmp::Reverse(move_sort_key(state, *m, ai_color, weights)));
    let keep = (ranked.len() / 3).max(3);
    ranked.truncate(keep);
    ranked
}

pub fn is_quiescence_move(state: &SearchState, mv: Move, ai_color: &str) -> bool {
    let (fm, to) = mv;
    if is_capture_move(
        &state.cells,
        &state.to_move,
        fm,
        to,
        &state.batyr_captured,
    ) {
        return true;
    }
    let enemy_biy = super::util::find_biy_cell(&state.cells, &opponent_color(&state.to_move));
    if let Some(enemy_biy) = enemy_biy {
        if state.to_move
            == state
                .cells
                .get(&fm)
                .and_then(|x| x.as_ref())
                .map(|n| piece_color_from_name(n.as_str()))
                .unwrap_or("")
        {
            if crate::rules::dict::dicts()
                .shatra_biy_captures
                .get(&to)
                .map(|m| m.values().any(|&v| v == enemy_biy))
                .unwrap_or(false)
            {
                return true;
            }
        }
    }
    let promo = if state.to_move == "белый" {
        WHITE_PROMOTION
    } else {
        BLACK_PROMOTION
    };
    if promo.contains(&to) {
        return true;
    }
    creates_mandatory_capture_for_opp(&state.cells, ai_color, mv)
}

pub fn is_must_search_move(
    state: &SearchState,
    mv: Move,
    ai_color: &str,
    mandatory: &HashSet<Move>,
) -> bool {
    if mandatory.contains(&mv) {
        return true;
    }
    if state.chain_cell.is_some() {
        return true;
    }
    let (fm, to) = mv;
    if captured_enemy_type(&state.cells, &state.to_move, fm, to, &state.batyr_captured)
        .as_deref()
        == Some("бий")
    {
        let (_, result) = child_state(state, fm, to);
        if result.game_over && we_won(&result, ai_color) {
            return true;
        }
    }
    false
}

pub fn is_tactical_secondary_move(state: &SearchState, mv: Move, ai_color: &str) -> bool {
    let (fm, to) = mv;
    if is_capture_move(
        &state.cells,
        &state.to_move,
        fm,
        to,
        &state.batyr_captured,
    ) {
        return true;
    }
    if state.to_move == ai_color {
        let opp = opponent_color(ai_color);
        let mut before = 0;
        for (&c, name) in &state.cells {
            let Some(name) = name else { continue };
            if piece_color_from_name(name) != ai_color {
                continue;
            }
            if safe_piece_type(name) == "бий" {
                continue;
            }
            if is_cell_capturable(&state.cells, &opp, c, &state.batyr_captured) {
                before += 1;
            }
        }
        if before > 0 {
            if let Some(child) = child_state(state, fm, to).0 {
                let mut after = 0;
                for (&c, name) in &child.cells {
                    let Some(name) = name else { continue };
                    if piece_color_from_name(name) != ai_color {
                        continue;
                    }
                    if safe_piece_type(name) == "бий" {
                        continue;
                    }
                    if is_cell_capturable(&child.cells, &opp, c, &child.batyr_captured) {
                        after += 1;
                    }
                }
                if after < before {
                    return true;
                }
            }
        }
    }
    is_quiescence_move(state, mv, ai_color)
}

pub fn move_limit(state: &SearchState, weights: &EvalWeights) -> i32 {
    let mut limit = super::MAX_MOVES_PER_NODE;
    if super::util::count_batyrs_for_color(&state.cells, &state.to_move) > 0 {
        limit += 8;
    }
    let _ = weights;
    limit
}

/// When legal moves fit in the search window, skip heuristic pruning.
pub fn needs_move_pruning(state: &SearchState, move_count: usize, weights: &EvalWeights) -> bool {
    move_count > move_limit(state, weights) as usize
}

pub fn select_moves_for_search(
    state: &SearchState,
    moves: Vec<Move>,
    ai_color: &str,
    maximizing: bool,
    start_time: Option<std::time::Instant>,
    time_limit: f64,
    tier3_cap: Option<i32>,
    weights: &EvalWeights,
) -> Vec<Move> {
    if moves.is_empty() {
        return moves;
    }
    let cap = tier3_cap.unwrap_or_else(|| move_limit(state, weights)) as usize;
    if moves.len() <= cap {
        return moves;
    }
    if moves.len() > 24 && super::time_exceeded(start_time, time_limit) {
        let mandatory = mandatory_moves_set(state);
        return moves
            .into_iter()
            .filter(|m| is_must_search_move(state, *m, ai_color, &mandatory))
            .collect();
    }

    let mandatory = mandatory_moves_set(state);
    let mut tier1 = Vec::new();
    let mut tier2 = Vec::new();
    let mut tier3 = Vec::new();
    let mut seen = HashSet::new();

    for mv in moves {
        if seen.contains(&mv) {
            continue;
        }
        if is_must_search_move(state, mv, ai_color, &mandatory) {
            tier1.push(mv);
            seen.insert(mv);
        } else if is_tactical_secondary_move(state, mv, ai_color) {
            tier2.push(mv);
            seen.insert(mv);
        } else {
            tier3.push(mv);
        }
    }

    let sort_color = if maximizing {
        ai_color.to_string()
    } else {
        opponent_color(ai_color)
    };
    tier2.sort_by_key(|m| {
        std::cmp::Reverse(move_sort_key(
            state,
            *m,
            &sort_color,
            weights,
        ))
    });
    tier3.sort_by_key(|m| {
        std::cmp::Reverse(move_sort_key(
            state,
            *m,
            &sort_color,
            weights,
        ))
    });

    let cap = tier3_cap.unwrap_or_else(|| move_limit(state, weights));
    let cap = cap as usize;
    tier1
        .into_iter()
        .chain(tier2)
        .chain(tier3.into_iter().take(cap))
        .collect()
}

pub fn ordered_moves(
    state: &SearchState,
    ai_color: &str,
    maximizing: bool,
    start_time: Option<std::time::Instant>,
    time_limit: f64,
    weights: &EvalWeights,
) -> Vec<Move> {
    let moves = get_legal_moves(state);
    if moves.is_empty() {
        return moves;
    }
    let narrow = !needs_move_pruning(state, moves.len(), weights);
    let candidates = if maximizing && state.to_move == ai_color && !narrow {
        filter_moves_for_ai(state, moves, ai_color, weights)
    } else {
        moves
    };
    if narrow {
        return candidates;
    }
    select_moves_for_search(
        state,
        candidates,
        ai_color,
        maximizing,
        start_time,
        time_limit,
        None,
        weights,
    )
}
pub fn pick_chain_move(state: &SearchState, ai_color: &str, weights: &EvalWeights) -> Option<Move> {
    let chain = state.chain_cell?;
    let hints = crate::rules::hints::get_hints(
        &state.cells,
        ai_color,
        chain,
        &state.batyr_captured,
        state.chain_cell,
    );
    let moves: Vec<Move> = hints
        .essential_positions
        .iter()
        .map(|&t| (chain, t))
        .collect();
    if moves.is_empty() {
        return None;
    }
    if moves.len() == 1 {
        return Some(moves[0]);
    }
    let mut safe = filter_moves_for_ai(state, moves, ai_color, weights);
    safe.sort_by_key(|m| std::cmp::Reverse(move_sort_key(state, *m, ai_color, weights)));
    safe.first().copied()
}

pub fn pick_winning_biy_capture(
    state: &SearchState,
    ai_color: &str,
) -> Option<Move> {
    for mv in get_legal_moves(state) {
        if captured_enemy_type(
            &state.cells,
            ai_color,
            mv.0,
            mv.1,
            &state.batyr_captured,
        )
        .as_deref()
            != Some("бий")
        {
            continue;
        }
        let (_, result) = child_state(state, mv.0, mv.1);
        if result.game_over && we_won(&result, ai_color) {
            return Some(mv);
        }
    }
    None
}

pub fn pick_best_mandatory_capture_fork(
    state: &SearchState,
    ai_color: &str,
    weights: &EvalWeights,
) -> Option<Move> {
    if state.to_move != ai_color || state.chain_cell.is_some() {
        return None;
    }
    let strict = get_strict_mandatory_captures(
        &state.cells,
        ai_color,
        &state.batyr_captured,
    );
    if strict.len() < 2 {
        return None;
    }
    let legal: HashSet<Move> = get_legal_moves(state).into_iter().collect();
    let options: Vec<Move> = strict.into_iter().filter(|m| legal.contains(m)).collect();
    if options.len() < 2 {
        return None;
    }
    let mut best_move: Option<Move> = None;
    let mut best_score = i32::MIN;
    for mv in options {
        let (chain_val, chain) = super::eval::simulate_capture_sequence(
            &state.cells,
            ai_color,
            mv,
            super::util::MANDATORY_CAPTURE_CHAIN_DEPTH,
            weights,
        );
        let score = chain_val * 100 + (chain.len() as i32) * 1_000;
        if score > best_score {
            best_score = score;
            best_move = Some(mv);
        }
    }
    best_move
}

pub fn has_obvious_win(cells: &crate::rules::dict::Cells, ai_color: &str) -> Option<Move> {
    let board = Board::new(cells.clone());
    for &(fm, to) in &get_all_mandatory_captures(&board, ai_color, &[]) {
        if let Some(p) = board.piece_at(fm) {
            if let Some(ec) = find_captured_enemy(cells, p.as_ref(), fm, to, &[]) {
                if cells
                    .get(&ec)
                    .and_then(|x| x.as_ref())
                    .map(|n| n.contains("бий"))
                    .unwrap_or(false)
                {
                    return Some((fm, to));
                }
            }
        }
    }
    None
}

pub fn weights() -> EvalWeights {
    default_weights()
}
