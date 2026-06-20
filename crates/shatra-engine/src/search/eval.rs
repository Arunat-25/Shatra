use std::collections::HashMap;

use crate::rules::board::Board;
use crate::rules::dict::{dicts, Cells};
use crate::rules::endgame::is_game_over;
use crate::rules::hints::{find_captured_enemy, get_all_mandatory_captures, get_hints};
use crate::rules::moves::process_move;

use super::geometry::{
    batyr_anchor_cells, biy_anchor_cells, biy_anchor_factor, count_opponent_shatras_in_own_fortress,
    count_own_pieces_in_fortress, in_danger_zone, in_side_file, is_biy_deploy_to_main_field,
    is_fortress_entry, is_fortress_shatra_deploy, is_main_field_cell, main_field_density,
    piece_color_from_name, safe_piece_type,
};
use super::state::{Move, SearchState};
use super::util::{
    child_state, clear_promotion_path, count_own_main_field_shatras,
    distance, find_biy_cell, get_all_captures_for_color, get_legal_moves,
    get_strict_mandatory_captures, is_capture_move, is_cell_capturable, mirror_cell,
    move_captures_cell, opponent_color, opponent_has_mass, piece_value, shatra_promotion_progress,
    we_lost, we_won, BLACK_PROMOTION, HANGING_WITHOUT_GAIN_PENALTY, LOSE_SCORE,
    MANDATORY_CAPTURE_CHAIN_DEPTH, WHITE_PROMOTION, WIN_SCORE,
};
use super::weights::{default_weights, EvalWeights};

pub const SHATRA_TABLE: [i32; 64] = [
    0, 0, 0, 0, 0, 0, 0, 0, 30, 36, 42, 42, 42, 42, 36, 30, 45, 54, 60, 60, 60, 60, 54, 45, 60, 72,
    84, 84, 84, 84, 72, 60, 75, 90, 105, 105, 105, 105, 90, 75, 90, 108, 126, 126, 126, 126, 108, 90,
    105, 126, 150, 150, 150, 150, 126, 105, 120, 150, 180, 210, 210, 180, 150, 120,
];
pub const BIY_TABLE: [i32; 64] = [
    180, 150, 120, 90, 90, 120, 150, 180, 150, 90, 60, 30, 30, 60, 90, 150, 120, 60, 0, -30, -30, 0,
    60, 120, 90, 30, -30, -60, -60, -30, 30, 90, 90, 30, -30, -60, -60, -30, 30, 90, 120, 60, 0, -30,
    -30, 0, 60, 120, 150, 90, 60, 30, 30, 60, 90, 150, 180, 150, 120, 90, 90, 120, 150, 180,
];
pub const BATYR_TABLE: [i32; 64] = [
    0, 0, 15, 30, 30, 15, 0, 0, 15, 30, 45, 60, 60, 45, 30, 15, 30, 45, 75, 90, 90, 75, 45, 30, 30,
    60, 90, 120, 120, 90, 60, 30, 30, 60, 90, 120, 120, 90, 60, 30, 30, 45, 75, 90, 90, 75, 45, 30,
    15, 30, 45, 60, 60, 45, 30, 15, 0, 0, 15, 30, 30, 15, 0, 0,
];

const FORTRESS_DEPLOY_PENALTY_MIN_SHATRAS: i32 = 8;

fn w() -> EvalWeights {
    default_weights()
}

pub fn evaluate(cells: &Cells, ai_color: &str, test_move: Option<Move>, weights: &EvalWeights) -> i32 {
    let end = is_game_over(&Board::new(cells.clone()), None, 0);
    if end.over {
        if let Some(ref winner) = end.winner_color {
            if winner == ai_color {
                return WIN_SCORE;
            }
            return LOSE_SCORE;
        }
    }

    let mut score = 0;
    let opp = opponent_color(ai_color);
    let our_biy = find_biy_cell(cells, ai_color);
    let enemy_biy = find_biy_cell(cells, &opp);
    let density = main_field_density(cells);
    let opp_mass = opponent_has_mass(cells, ai_color);

    for (&cell_id, name) in cells {
        let Some(name) = name else { continue };
        let color = piece_color_from_name(name);
        let pt = safe_piece_type(name);
        let sign = if color == ai_color { 1 } else { -1 };
        score += sign * piece_value(weights, pt);
        let idx = if color == "черный" {
            mirror_cell(cell_id) as usize
        } else {
            cell_id as usize
        };
        let on_danger = opp_mass && color == ai_color && in_danger_zone(cell_id);

        match pt {
            "шатра" => {
                score += sign
                    * shatra_promotion_progress(color, cell_id)
                    * weights.promotion_progress_weight;
                if clear_promotion_path(cells, color, cell_id) {
                    score += sign * 50;
                }
                let promo = if color == "белый" {
                    WHITE_PROMOTION
                } else {
                    BLACK_PROMOTION
                };
                if promo.contains(&cell_id) {
                    score += sign * weights.promotion_bonus;
                }
            }
            "бий" => {
                if !on_danger {
                    score += sign * (BIY_TABLE[idx] as f64 * weights.position_scale) as i32;
                }
                if biy_anchor_cells(color).contains(&cell_id) {
                    let k = biy_anchor_factor(density, weights.crowded_main_field_threshold);
                    score += sign * (weights.biy_anchor_bonus as f64 * k) as i32;
                }
            }
            "батыр" => {
                if batyr_anchor_cells(color).contains(&cell_id)
                    && !is_cell_capturable(cells, &opponent_color(color), cell_id, &[])
                {
                    score += sign * weights.batyr_anchor_bonus;
                } else if opp_mass
                    && in_side_file(cell_id)
                    && !is_cell_capturable(cells, &opponent_color(color), cell_id, &[])
                {
                    score += sign * weights.side_file_batyr_bonus;
                }
            }
            _ => {}
        }

        if opp_mass
            && pt == "шатра"
            && in_side_file(cell_id)
            && !is_cell_capturable(cells, &opponent_color(color), cell_id, &[])
        {
            score += sign * weights.side_file_shatra_bonus;
        }

        if on_danger {
            score -= weights.danger_zone_penalty;
        }
    }

    if let Some(biy) = our_biy {
        if is_cell_capturable(cells, &opp, biy, &[]) {
            score -= weights.biy_loss_penalty;
        }
    }
    if let Some(biy) = enemy_biy {
        if is_cell_capturable(cells, ai_color, biy, &[]) {
            score += weights.biy_loss_penalty / 2;
        }
    }

    for (&cell, name) in cells {
        let Some(name) = name else { continue };
        if piece_color_from_name(name) != ai_color {
            continue;
        }
        let pt = safe_piece_type(name);
        if pt == "бий" {
            continue;
        }
        if is_cell_capturable(cells, &opp, cell, &[]) {
            score -= weights.hanging_penalty + piece_value(weights, pt) / 2;
        }
    }

    score += evaluate_biy_threats(cells, ai_color);
    score -= evaluate_fortress_intrusion(cells, ai_color, weights);

    if let Some(mv) = test_move {
        score += evaluate_forced_trap(cells, ai_color, mv, weights);
        score += evaluate_chain_potential(cells, ai_color, mv, weights);
    }

    if let Some(our_biy) = our_biy {
        if !is_cell_capturable(cells, &opp, our_biy, &[]) {
            let board = Board::new(cells.clone());
            for (&c, name) in cells {
                let Some(name) = name else { continue };
                if piece_color_from_name(name) != opp.as_str() {
                    continue;
                }
                let pt = safe_piece_type(name);
                if pt != "шатра" && pt != "батыр" {
                    continue;
                }
                if distance(c, our_biy) > 2 {
                    continue;
                }
                let piece = match board.piece_at(c) {
                    Some(p) => p,
                    None => continue,
                };
                let is_threat = if pt == "шатра" || pt == "бий" {
                    dicts()
                        .shatra_biy_captures
                        .get(&c)
                        .map(|m| m.values().any(|&v| v == our_biy))
                        .unwrap_or(false)
                } else {
                    let hints = get_hints(cells, &opp, c, &[], None);
                    hints.essential_positions.contains(&our_biy)
                };
                if is_threat {
                    score -= weights.biy_loss_penalty / 3;
                }
            }
        }
    }

    score
}

fn evaluate_biy_threats(cells: &Cells, ai_color: &str) -> i32 {
    let mut score = 0;
    let opp = opponent_color(ai_color);
    for (&cell, name) in cells {
        let Some(name) = name else { continue };
        let pt = safe_piece_type(name);
        if pt != "шатра" && pt != "батыр" {
            continue;
        }
        let pc = piece_color_from_name(name);
        let tgt = if pc == ai_color {
            opp.as_str()
        } else {
            ai_color
        };
        let Some(biy) = find_biy_cell(cells, tgt) else {
            continue;
        };
        let d = distance(cell, biy);
        if d <= 2 {
            score += if pc == ai_color {
                150 * (3 - d)
            } else {
                -200 * (3 - d)
            };
        }
    }
    score
}

fn evaluate_fortress_intrusion(cells: &Cells, ai_color: &str, weights: &EvalWeights) -> i32 {
    if count_own_pieces_in_fortress(cells, ai_color) > 0 {
        return 0;
    }
    let intruders = count_opponent_shatras_in_own_fortress(cells, ai_color);
    if intruders == 0 {
        return 0;
    }
    intruders * weights.fortress_intrusion_penalty
}

pub fn simulate_capture_sequence(
    cells: &Cells,
    color: &str,
    start_move: Move,
    max_depth: i32,
    weights: &EvalWeights,
) -> (i32, Vec<Move>) {
    let (fm, to) = start_move;
    let board = Board::new(cells.clone());
    let piece = match board.piece_at(fm) {
        Some(p) => p,
        None => return (0, vec![]),
    };
    let captured = find_captured_enemy(cells, piece.as_ref(), fm, to, &[]);
    if captured.is_none() || cells.get(&captured.unwrap()).and_then(|x| x.as_ref()).is_none() {
        return (0, vec![]);
    }

    let mut empty_history = HashMap::new();
    let result = process_move(
        cells,
        color,
        fm,
        to,
        None,
        &[],
        &mut empty_history,
        0,
    );
    let Some(new_cells) = result.updated_positions else {
        return (0, vec![]);
    };
    if new_cells == *cells {
        return (0, vec![]);
    }

    let mut chain = vec![start_move];
    let victim_name = cells.get(&captured.unwrap()).and_then(|x| x.as_ref());
    let mut total_value = victim_name
        .map(|n| piece_value(weights, safe_piece_type(n)))
        .unwrap_or(0);
    let mut new_cells = new_cells;
    let mut next_chain = result.position_for_mandatory_capture;

    for _ in 0..(max_depth - 1) {
        let Some(fm_c) = next_chain else { break };
        let name = new_cells.get(&fm_c).and_then(|x| x.as_ref());
        let Some(name) = name else { break };
        if piece_color_from_name(name) != color {
            break;
        }
        let board = Board::new(new_cells.clone());
        let piece = match board.piece_at(fm_c) {
            Some(p) => p,
            None => break,
        };

        let mut best_step: Option<(i32, Move, Cells, Option<i32>)> = None;
        if let Some(targets) = dicts().shatra_biy_captures.get(&fm_c) {
            for (&to_c, &ec) in targets {
                if new_cells.get(&to_c).and_then(|x| x.as_ref()).is_some()
                    || !piece.can_capture(&new_cells, fm_c, to_c, &[])
                {
                    continue;
                }
                let v_name = new_cells.get(&ec).and_then(|x| x.as_ref());
                let Some(v_name) = v_name else { continue };
                let mut hist = HashMap::new();
                let res = process_move(
                    &new_cells,
                    color,
                    fm_c,
                    to_c,
                    Some(fm_c),
                    &[],
                    &mut hist,
                    0,
                );
                let Some(updated) = res.updated_positions else { continue };
                if updated == new_cells {
                    continue;
                }
                let step_val = piece_value(weights, safe_piece_type(v_name));
                let cand = (step_val, (fm_c, to_c), updated, res.position_for_mandatory_capture);
                if best_step.as_ref().map(|b| cand.0 > b.0).unwrap_or(true) {
                    best_step = Some(cand);
                }
            }
        }

        let Some((step_val, step_move, updated, nc)) = best_step else {
            break;
        };
        total_value += step_val;
        chain.push(step_move);
        new_cells = updated;
        next_chain = nc;
    }

    (total_value, chain)
}

fn evaluate_forced_trap(cells: &Cells, ai_color: &str, test_move: Move, weights: &EvalWeights) -> i32 {
    let (fm, to) = test_move;
    let opp = opponent_color(ai_color);
    let mut hist = HashMap::new();
    let result = process_move(cells, &opp, fm, to, None, &[], &mut hist, 0);
    let Some(new_cells) = result.updated_positions else {
        return 0;
    };
    let board = Board::new(new_cells.clone());
    let opp_mandatory = get_all_mandatory_captures(&board, &opp, &[]);
    if opp_mandatory.is_empty() {
        return 0;
    }
    let state = SearchState::new(new_cells.clone(), &opp, None, vec![], None);
    let all_opp = get_legal_moves(&state);
    if opp_mandatory.len() == all_opp.len() && !opp_mandatory.is_empty() {
        let mut best_for_us = i32::MIN;
        for &(opp_fm, opp_to) in &opp_mandatory {
            let mut hist2 = HashMap::new();
            let opp_res = process_move(
                &new_cells,
                &opp,
                opp_fm,
                opp_to,
                None,
                &[],
                &mut hist2,
                0,
            );
            let Some(after_opp) = opp_res.updated_positions else {
                continue;
            };
            let our_caps = get_all_captures_for_color(&after_opp, ai_color, &[]);
            let mut chain_value = 0;
            let mut biy_threat = 0;
            for &(c_fm, c_to, c_captured) in &our_caps {
                if c_captured.map(|c| {
                    after_opp
                        .get(&c)
                        .and_then(|x| x.as_ref())
                        .map(|n| n.contains("бий"))
                        .unwrap_or(false)
                }).unwrap_or(false)
                {
                    biy_threat = weights.biy_loss_penalty / 2;
                } else if let Some(c) = c_captured {
                    if let Some(v_name) = after_opp.get(&c).and_then(|x| x.as_ref()) {
                        chain_value += piece_value(weights, safe_piece_type(v_name));
                    }
                }
            }
            if !our_caps.is_empty() {
                let best_cap = our_caps
                    .iter()
                    .max_by_key(|x| {
                        x.2.and_then(|c| {
                            after_opp
                                .get(&c)
                                .and_then(|v| v.as_ref())
                                .map(|n| piece_value(weights, safe_piece_type(n)))
                        })
                        .unwrap_or(0)
                    })
                    .unwrap();
                let sim_val = simulate_capture_sequence(
                    &after_opp,
                    ai_color,
                    (best_cap.0, best_cap.1),
                    4,
                    weights,
                )
                .0;
                chain_value = chain_value.max(sim_val);
            }
            best_for_us = best_for_us.max(chain_value + biy_threat);
        }
        if best_for_us > 0 {
            return weights.forced_trap_bonus + best_for_us.min(10_000);
        }
    }
    let board = Board::new(new_cells.clone());
    for &(opp_fm, opp_to) in &opp_mandatory {
        if let Some(opp_p) = board.piece_at(opp_fm) {
            if let Some(opp_cap) =
                find_captured_enemy(&new_cells, opp_p.as_ref(), opp_fm, opp_to, &[])
            {
                if new_cells
                    .get(&opp_cap)
                    .and_then(|x| x.as_ref())
                    .map(|n| n.contains("бий"))
                    .unwrap_or(false)
                {
                    return weights.forced_trap_bonus / 2;
                }
            }
        }
    }
    0
}

pub fn evaluate_chain_potential(
    cells: &Cells,
    ai_color: &str,
    mv: Move,
    weights: &EvalWeights,
) -> i32 {
    let (fm, to) = mv;
    let board = Board::new(cells.clone());
    let piece = match board.piece_at(fm) {
        Some(p) => p,
        None => return 0,
    };
    let captured = find_captured_enemy(cells, piece.as_ref(), fm, to, &[]);
    if captured.is_some() {
        let (value, chain) =
            simulate_capture_sequence(cells, ai_color, mv, 4, weights);
        if chain.len() >= 2 {
            return weights.chain_capture_bonus + value.min(5_000);
        }
        return value / 2;
    }
    let mut hist = HashMap::new();
    let result = process_move(cells, ai_color, fm, to, None, &[], &mut hist, 0);
    let Some(updated) = result.updated_positions else {
        return 0;
    };
    let new_caps = get_all_captures_for_color(&updated, ai_color, &[]);
    let old_caps = get_all_captures_for_color(cells, ai_color, &[]);
    if new_caps.len() > old_caps.len() {
        let best_new = new_caps
            .iter()
            .filter(|c| !old_caps.contains(c))
            .map(|c| {
                c.2.and_then(|cell| {
                    updated
                        .get(&cell)
                        .and_then(|x| x.as_ref())
                        .map(|n| piece_value(weights, safe_piece_type(n)))
                })
                .unwrap_or(0)
            })
            .max()
            .unwrap_or(0);
        return weights.sacrifice_setup_bonus / 2 + best_new / 2;
    }
    0
}

pub fn evaluate_hanging_sacrifice(
    state: &SearchState,
    mv: Move,
    ai_color: &str,
    weights: &EvalWeights,
) -> i32 {
    let (fm, to) = mv;
    let piece = state.cells.get(&fm).and_then(|x| x.as_ref());
    let Some(piece) = piece else { return 0 };
    if piece_color_from_name(piece) != ai_color {
        return 0;
    }
    let Some(child) = child_state(state, fm, to).0 else {
        return 0;
    };
    let opp = opponent_color(ai_color);
    if !is_cell_capturable(&child.cells, &opp, to, &child.batyr_captured) {
        return 0;
    }
    if child.chain_cell.is_some() && child.to_move == ai_color {
        return 0;
    }

    let our_lost = piece_value(weights, safe_piece_type(piece));
    let opp_state = SearchState {
        cells: child.cells.clone(),
        to_move: opp.clone(),
        chain_cell: None,
        batyr_captured: vec![],
        position_history: state.position_history.clone(),
    };
    let mut nets = Vec::new();

    for opp_move in get_legal_moves(&opp_state) {
        if !move_captures_cell(
            &child.cells,
            opp_move.0,
            opp_move.1,
            to,
            &child.batyr_captured,
        ) {
            continue;
        }
        let Some(after_opp) = child_state(&opp_state, opp_move.0, opp_move.1).0 else {
            continue;
        };
        if after_opp.to_move != ai_color {
            nets.push(-our_lost);
            continue;
        }
        let mut best_chain = 0;
        for cap_move in get_strict_mandatory_captures(
            &after_opp.cells,
            ai_color,
            &after_opp.batyr_captured,
        ) {
            let val = simulate_capture_sequence(
                &after_opp.cells,
                ai_color,
                cap_move,
                MANDATORY_CAPTURE_CHAIN_DEPTH,
                weights,
            )
            .0;
            best_chain = best_chain.max(val);
        }
        nets.push(best_chain - our_lost);
    }

    if nets.is_empty() {
        return -HANGING_WITHOUT_GAIN_PENALTY;
    }
    let net = *nets.iter().min().unwrap();
    if net > 0 {
        return net;
    }
    if net == 0 {
        return weights.even_trade_bonus;
    }
    net
}

pub fn fortress_deploy_penalty_applies(cells: &Cells, ai_color: &str) -> bool {
    count_own_main_field_shatras(cells, ai_color) > FORTRESS_DEPLOY_PENALTY_MIN_SHATRAS
}

fn cells_defended_by_deploy(state: &SearchState, after_cells: &Cells, ai_color: &str) -> Vec<i32> {
    let opp = opponent_color(ai_color);
    let mut defended = Vec::new();
    for (&cell, name) in &state.cells {
        let Some(name) = name else { continue };
        if piece_color_from_name(name) != ai_color {
            continue;
        }
        if !is_main_field_cell(cell) {
            continue;
        }
        if is_cell_capturable(&state.cells, &opp, cell, &state.batyr_captured)
            && !is_cell_capturable(after_cells, &opp, cell, &[])
        {
            defended.push(cell);
        }
    }
    defended
}

fn can_defend_cell_with_field_piece(
    state: &SearchState,
    ai_color: &str,
    threatened_cell: i32,
    exclude_from: Option<i32>,
) -> bool {
    let opp = opponent_color(ai_color);
    if !is_cell_capturable(&state.cells, &opp, threatened_cell, &state.batyr_captured) {
        return true;
    }
    for (&fm, name) in &state.cells {
        if exclude_from == Some(fm) {
            continue;
        }
        let Some(name) = name else { continue };
        if piece_color_from_name(name) != ai_color {
            continue;
        }
        if !is_main_field_cell(fm) {
            continue;
        }
        let hints = get_hints(
            &state.cells,
            ai_color,
            fm,
            &state.batyr_captured,
            state.chain_cell,
        );
        for &alt_to in &hints.essential_positions {
            let (child_opt, result) = child_state(state, fm, alt_to);
            let Some(child) = child_opt else { continue };
            if result.game_over && we_lost(&result, ai_color) {
                continue;
            }
            let defended_piece = child.cells.get(&threatened_cell).and_then(|x| x.as_ref());
            if defended_piece.map(|n| piece_color_from_name(n) != ai_color).unwrap_or(true) {
                continue;
            }
            if !is_cell_capturable(&child.cells, &opp, threatened_cell, &child.batyr_captured) {
                return true;
            }
        }
    }
    false
}

pub fn fortress_deploy_justified(state: &SearchState, mv: Move, ai_color: &str, weights: &EvalWeights) -> bool {
    let (fm, to) = mv;
    if !is_fortress_shatra_deploy(fm, to, ai_color) {
        return false;
    }
    if evaluate_hanging_sacrifice(state, mv, ai_color, weights) > 0 {
        return true;
    }
    if is_capture_move(&state.cells, ai_color, fm, to, &state.batyr_captured) {
        return true;
    }
    let Some(child) = child_state(state, fm, to).0 else {
        return false;
    };
    let opp = opponent_color(ai_color);
    if is_cell_capturable(&child.cells, &opp, to, &child.batyr_captured) {
        return false;
    }
    let defended = cells_defended_by_deploy(state, &child.cells, ai_color);
    if defended.is_empty() {
        return false;
    }
    for cell in defended {
        if can_defend_cell_with_field_piece(state, ai_color, cell, Some(fm)) {
            return false;
        }
    }
    true
}

pub fn fortress_entry_piece_bonus(piece_name: &str, weights: &EvalWeights) -> i32 {
    if safe_piece_type(piece_name) != "шатра" {
        return 0;
    }
    weights.fortress_entry_shatra_bonus.min(weights.piece_shatra - 1)
}

pub fn fortress_entry_search_adjustment(
    state: &SearchState,
    mv: Move,
    ai_color: &str,
    weights: &EvalWeights,
) -> i32 {
    let (fm, to) = mv;
    let mover = &state.to_move;
    if mover != ai_color && mover != &opponent_color(ai_color) {
        return 0;
    }
    let piece = state.cells.get(&fm).and_then(|x| x.as_ref());
    let Some(piece) = piece else { return 0 };
    if piece_color_from_name(piece) != mover.as_str() {
        return 0;
    }
    if !is_fortress_entry(fm, to, mover) {
        return 0;
    }
    let bonus = fortress_entry_piece_bonus(piece, weights);
    if bonus == 0 {
        return 0;
    }
    if mover == ai_color {
        return bonus;
    }
    if count_own_pieces_in_fortress(&state.cells, ai_color) == 0 {
        return -weights.fortress_intrusion_penalty;
    }
    -bonus
}

pub fn fortress_deploy_search_penalty(
    state: &SearchState,
    mv: Move,
    ai_color: &str,
    weights: &EvalWeights,
) -> i32 {
    let (fm, to) = mv;
    let piece = state.cells.get(&fm).and_then(|x| x.as_ref());
    let Some(piece) = piece else { return 0 };
    if state.to_move != ai_color || safe_piece_type(piece) != "шатра" {
        return 0;
    }
    if !is_fortress_shatra_deploy(fm, to, ai_color) {
        return 0;
    }
    if fortress_deploy_justified(state, mv, ai_color, weights) {
        return 0;
    }
    if !fortress_deploy_penalty_applies(&state.cells, ai_color) {
        return 0;
    }
    weights.fortress_deploy_penalty
}

pub fn move_exposes_biy(state: &SearchState, mv: Move, ai_color: &str) -> bool {
    let (child_opt, res) = child_state(state, mv.0, mv.1);
    let Some(child) = child_opt else {
        return true;
    };
    if res.game_over {
        return we_lost(&res, ai_color);
    }
    let Some(our) = find_biy_cell(&child.cells, ai_color) else {
        return false;
    };
    let opp = opponent_color(ai_color);
    if is_cell_capturable(&child.cells, &opp, our, &child.batyr_captured) {
        return true;
    }
    if child.to_move == opp {
        let board = Board::new(child.cells.clone());
        for &(f, t) in &get_all_mandatory_captures(&board, &opp, &[]) {
            if let Some(p) = board.piece_at(f) {
                if find_captured_enemy(&child.cells, p.as_ref(), f, t, &child.batyr_captured)
                    == Some(our)
                {
                    return true;
                }
            }
        }
    }
    false
}

pub fn biy_capture_net_if_recaptured(
    state: &SearchState,
    mv: Move,
    ai_color: &str,
    weights: &EvalWeights,
) -> Option<i32> {
    let (fm, to) = mv;
    let piece = state.cells.get(&fm).and_then(|x| x.as_ref());
    let Some(piece) = piece else { return None };
    if safe_piece_type(piece) != "бий" || state.to_move != ai_color {
        return None;
    }
    if !is_capture_move(&state.cells, ai_color, fm, to, &state.batyr_captured) {
        return None;
    }
    let victim = captured_enemy_type(&state.cells, ai_color, fm, to, &state.batyr_captured)?;
    if victim == "бий" {
        return Some(WIN_SCORE);
    }
    let (_, res) = child_state(state, fm, to);
    if res.game_over && we_won(&res, ai_color) {
        return Some(WIN_SCORE);
    }
    let gained = piece_value(weights, &victim);
    if !is_cell_capturable(
        &res.updated_positions.clone().unwrap_or(state.cells.clone()),
        &opponent_color(ai_color),
        to,
        &[],
    ) {
        return Some(gained);
    }
    Some(gained - weights.piece_biy)
}

fn captured_enemy_type(
    cells: &Cells,
    color: &str,
    fm: i32,
    to: i32,
    batyr_caps: &[i32],
) -> Option<String> {
    super::util::captured_enemy_type(cells, color, fm, to, batyr_caps)
}

pub fn mandatory_capture_chain_bonus(
    state: &SearchState,
    mv: Move,
    ai_color: &str,
    weights: &EvalWeights,
) -> i32 {
    if state.chain_cell.is_some() {
        return 0;
    }
    if state.to_move != ai_color {
        return 0;
    }
    let mandatory = mandatory_moves_set(state);
    if !mandatory.contains(&mv) {
        return 0;
    }
    let (chain_val, chain) = simulate_capture_sequence(
        &state.cells,
        ai_color,
        mv,
        MANDATORY_CAPTURE_CHAIN_DEPTH,
        weights,
    );
    chain_val * 40 + (chain.len() as i32) * 2_000
}

fn mandatory_moves_set(state: &SearchState) -> std::collections::HashSet<Move> {
    super::util::mandatory_moves_set(state)
}

pub fn creates_mandatory_capture_for_opp(cells: &Cells, ai_color: &str, mv: Move) -> bool {
    let (fm, to) = mv;
    let mut hist = HashMap::new();
    let result = process_move(cells, ai_color, fm, to, None, &[], &mut hist, 0);
    let Some(updated) = result.updated_positions else {
        return false;
    };
    let opp = opponent_color(ai_color);
    !get_strict_mandatory_captures(&updated, &opp, &[]).is_empty()
}

pub fn is_deprioritized_move(
    state: &SearchState,
    mv: Move,
    ai_color: &str,
    weights: &EvalWeights,
) -> bool {
    if state.to_move != ai_color {
        return false;
    }
    let (fm, to) = mv;
    let piece = state.cells.get(&fm).and_then(|x| x.as_ref());
    let Some(piece) = piece else { return false };
    if piece_color_from_name(piece) != ai_color {
        return false;
    }
    let pt = safe_piece_type(piece);
    if pt == "бий" && main_field_density(&state.cells) >= weights.crowded_main_field_threshold {
        if is_biy_deploy_to_main_field(fm, to, ai_color) {
            return true;
        }
    }
    if pt == "шатра" && is_fortress_shatra_deploy(fm, to, ai_color) {
        if fortress_deploy_penalty_applies(&state.cells, ai_color)
            && !fortress_deploy_justified(state, mv, ai_color, weights)
        {
            return true;
        }
    }
    false
}

// re-export evaluate with default weights for callers
pub fn evaluate_default(cells: &Cells, ai_color: &str, test_move: Option<Move>) -> i32 {
    evaluate(cells, ai_color, test_move, &w())
}
