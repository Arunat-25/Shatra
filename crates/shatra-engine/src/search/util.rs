use std::collections::HashMap;

use crate::rules::board::Board;
use crate::rules::dict::{dicts, Cells};
use crate::rules::domain::opponent;
use crate::rules::hints::{
    find_captured_enemy, get_all_mandatory_captures, get_hints,
};
use crate::rules::moves::{process_move, ProcessMoveResult};

use super::geometry::{is_main_field_cell, piece_color_from_name, safe_piece_type};
use super::state::{Move, SearchState};
use super::weights::EvalWeights;

pub const WIN_SCORE: i32 = 1_000_000;
pub const LOSE_SCORE: i32 = -1_000_000;
pub const HANGING_WITHOUT_GAIN_PENALTY: i32 = 500_000;
pub const MANDATORY_CAPTURE_CHAIN_DEPTH: i32 = 16;
pub const WHITE_PROMOTION: &[i32] = &[1, 2, 3];
pub const BLACK_PROMOTION: &[i32] = &[60, 61, 62];

pub fn opponent_color(color: &str) -> String {
    opponent(color)
}

pub fn count_pieces(cells: &Cells) -> i32 {
    cells.values().filter(|v| v.is_some()).count() as i32
}

pub fn count_color_pieces(cells: &Cells, color: &str) -> i32 {
    cells
        .values()
        .filter(|v| {
            v.as_ref()
                .map(|n| piece_color_from_name(n) == color)
                .unwrap_or(false)
        })
        .count() as i32
}

pub fn opponent_has_mass(cells: &Cells, ai_color: &str) -> bool {
    count_color_pieces(cells, &opponent_color(ai_color))
        > super::geometry::OPPONENT_MASS_THRESHOLD
}

pub fn mirror_cell(cell: i32) -> i32 {
    (7 - cell / 8) * 8 + (cell % 8)
}

pub fn distance(c1: i32, c2: i32) -> i32 {
    (c1 / 8 - c2 / 8).abs() + (c1 % 8 - c2 % 8).abs()
}

pub fn find_biy_cell(cells: &Cells, color: &str) -> Option<i32> {
    for (&c, n) in cells {
        if let Some(name) = n {
            if name.contains("бий") && piece_color_from_name(name) == color {
                return Some(c);
            }
        }
    }
    None
}

pub fn clear_promotion_path(cells: &Cells, color: &str, cell: i32) -> bool {
    let row = cell / 8;
    let col = cell % 8;
    let target_rows: Vec<i32> = if color == "белый" {
        (0..row).rev().collect()
    } else {
        ((row + 1)..8).collect()
    };
    for r in target_rows {
        if cells.get(&(r * 8 + col)).and_then(|x| x.as_ref()).is_some() {
            return false;
        }
    }
    true
}

pub fn shatra_promotion_progress(color: &str, cell: i32) -> i32 {
    let row = cell / 8;
    if color == "белый" {
        if row <= 1 {
            120
        } else if row == 2 {
            55
        } else if row == 3 {
            25
        } else {
            0
        }
    } else if row >= 6 {
        120
    } else if row == 5 {
        55
    } else if row == 4 {
        25
    } else {
        0
    }
}

pub fn we_won(result: &ProcessMoveResult, color: &str) -> bool {
    result.game_over && result.winner_color.as_deref() == Some(color)
}

pub fn we_lost(result: &ProcessMoveResult, color: &str) -> bool {
    result.game_over
        && result
            .winner_color
            .as_ref()
            .is_some_and(|w| w != color)
}

pub fn terminal_score(result: &ProcessMoveResult, ai_color: &str) -> Option<i32> {
    if !result.game_over {
        return None;
    }
    if we_won(result, ai_color) {
        return Some(WIN_SCORE);
    }
    if we_lost(result, ai_color) {
        return Some(LOSE_SCORE);
    }
    Some(0)
}

pub fn apply_process_move(state: &SearchState, fm: i32, to: i32) -> ProcessMoveResult {
    let mut empty_history = HashMap::new();
    process_move(
        &state.cells,
        &state.to_move,
        fm,
        to,
        state.chain_cell,
        &state.batyr_captured,
        &mut empty_history,
        0,
    )
}

pub fn child_state(
    state: &SearchState,
    fm: i32,
    to: i32,
) -> (Option<SearchState>, ProcessMoveResult) {
    let result = apply_process_move(state, fm, to);
    if result.updated_positions.is_none() {
        return (None, result);
    }
    let updated = result.updated_positions.clone().unwrap();
    let nc = result.position_for_mandatory_capture;
    let nm = result
        .movers_color
        .clone()
        .unwrap_or_else(|| state.to_move.clone());
    if nc.is_some() && nm == state.to_move {
        let child = SearchState {
            cells: updated,
            to_move: state.to_move.clone(),
            chain_cell: nc,
            batyr_captured: result.captured_pieces.clone(),
            position_history: state.position_history.clone(),
        };
        return (Some(child), result);
    }
    let child = SearchState {
        cells: updated,
        to_move: nm,
        chain_cell: None,
        batyr_captured: vec![],
        position_history: state.position_history.clone(),
    };
    (Some(child), result)
}

pub fn get_legal_moves(state: &SearchState) -> Vec<Move> {
    let mut moves = Vec::new();
    for (&c, n) in &state.cells {
        let Some(name) = n else { continue };
        if piece_color_from_name(name) != state.to_move.as_str() {
            continue;
        }
        let hints = get_hints(
            &state.cells,
            &state.to_move,
            c,
            &state.batyr_captured,
            state.chain_cell,
        );
        for &t in &hints.essential_positions {
            moves.push((c, t));
        }
    }
    moves
}

pub fn is_capture_move(cells: &Cells, _color: &str, fm: i32, to: i32, batyr_caps: &[i32]) -> bool {
    let board = Board::new(cells.clone());
    let piece = match board.piece_at(fm) {
        Some(p) => p,
        None => return false,
    };
    let pt = cells
        .get(&fm)
        .and_then(|x| x.as_ref())
        .map(|n| safe_piece_type(n))
        .unwrap_or("");
    if pt == "шатра" || pt == "бий" {
        return dicts()
            .shatra_biy_captures
            .get(&fm)
            .map(|m| m.contains_key(&to))
            .unwrap_or(false);
    }
    piece.can_capture(cells, fm, to, batyr_caps)
}

pub fn captured_enemy_type(
    cells: &Cells,
    color: &str,
    fm: i32,
    to: i32,
    batyr_caps: &[i32],
) -> Option<String> {
    let board = Board::new(cells.clone());
    let piece = board.piece_at(fm)?;
    let ec = find_captured_enemy(cells, piece.as_ref(), fm, to, batyr_caps)?;
    let victim = cells.get(&ec)?.as_ref()?;
    if piece_color_from_name(victim) == color {
        return None;
    }
    Some(safe_piece_type(victim).to_string())
}

pub fn move_captures_cell(
    cells: &Cells,
    fm: i32,
    to: i32,
    target: i32,
    batyr_caps: &[i32],
) -> bool {
    let board = Board::new(cells.clone());
    let piece = match board.piece_at(fm) {
        Some(p) => p,
        None => return false,
    };
    find_captured_enemy(cells, piece.as_ref(), fm, to, batyr_caps) == Some(target)
}

pub fn get_strict_mandatory_captures(cells: &Cells, color: &str, batyr_caps: &[i32]) -> Vec<Move> {
    let board = Board::new(cells.clone());
    get_all_mandatory_captures(&board, color, batyr_caps)
        .into_iter()
        .filter(|&(fm, _)| {
            cells
                .get(&fm)
                .and_then(|x| x.as_ref())
                .map(|n| safe_piece_type(n) != "бий")
                .unwrap_or(false)
        })
        .collect()
}

pub fn mandatory_moves_set(state: &SearchState) -> std::collections::HashSet<Move> {
    let board = Board::new(state.cells.clone());
    get_all_mandatory_captures(&board, &state.to_move, &state.batyr_captured)
        .into_iter()
        .collect()
}

pub fn count_batyrs_for_color(cells: &Cells, color: &str) -> i32 {
    cells
        .values()
        .filter(|v| {
            v.as_ref()
                .map(|n| n.contains("батыр") && piece_color_from_name(n) == color)
                .unwrap_or(false)
        })
        .count() as i32
}

pub fn count_own_main_field_shatras(cells: &Cells, ai_color: &str) -> i32 {
    cells
        .iter()
        .filter(|(&cell, n)| {
            n.as_ref().map_or(false, |name| {
                piece_color_from_name(name) == ai_color
                    && safe_piece_type(name) == "шатра"
                    && is_main_field_cell(cell)
            })
        })
        .count() as i32
}

pub fn piece_value(w: &EvalWeights, pt: &str) -> i32 {
    w.piece_value(pt)
}

pub fn is_cell_capturable(cells: &Cells, by_color: &str, target_cell: i32, batyr_caps: &[i32]) -> bool {
    if cells.get(&target_cell).and_then(|x| x.as_ref()).is_none() {
        return false;
    }
    let board = Board::new(cells.clone());
    for &(fm, to) in &get_all_mandatory_captures(&board, by_color, batyr_caps) {
        if let Some(p) = board.piece_at(fm) {
            if find_captured_enemy(cells, p.as_ref(), fm, to, batyr_caps) == Some(target_cell) {
                return true;
            }
        }
    }
    for (&fm, name) in cells {
        let Some(name) = name else { continue };
        if piece_color_from_name(name) != by_color {
            continue;
        }
        let piece = match board.piece_at(fm) {
            Some(p) => p,
            None => continue,
        };
        let pt = safe_piece_type(name);
        if pt == "шатра" || pt == "бий" {
            if let Some(caps) = dicts().shatra_biy_captures.get(&fm) {
                for (&to, &ec) in caps {
                    if ec == target_cell && piece.can_capture(cells, fm, to, batyr_caps) {
                        return true;
                    }
                }
            }
        } else if pt == "батыр" {
            let hints = get_hints(cells, by_color, fm, batyr_caps, None);
            for &to in &hints.essential_positions {
                if piece.can_capture(cells, fm, to, batyr_caps)
                    && find_captured_enemy(cells, piece.as_ref(), fm, to, batyr_caps)
                        == Some(target_cell)
                {
                    return true;
                }
            }
        }
    }
    false
}

pub fn get_all_captures_for_color(
    cells: &Cells,
    color: &str,
    batyr_caps: &[i32],
) -> Vec<(i32, i32, Option<i32>)> {
    let mut captures = Vec::new();
    let board = Board::new(cells.clone());
    for &(fm, to) in &get_all_mandatory_captures(&board, color, batyr_caps) {
        if let Some(p) = board.piece_at(fm) {
            captures.push((fm, to, find_captured_enemy(cells, p.as_ref(), fm, to, batyr_caps)));
        }
    }
    for (&fm, name) in cells {
        let Some(name) = name else { continue };
        if piece_color_from_name(name) != color {
            continue;
        }
        let pt = safe_piece_type(name);
        if pt != "шатра" && pt != "бий" {
            continue;
        }
        let piece = match board.piece_at(fm) {
            Some(p) => p,
            None => continue,
        };
        if let Some(caps) = dicts().shatra_biy_captures.get(&fm) {
            for (&to, &ec) in caps {
                let victim = cells.get(&ec).and_then(|x| x.as_ref());
                if victim.map(|v| piece_color_from_name(v) != color).unwrap_or(false)
                    && cells.get(&to).and_then(|x| x.as_ref()).is_none()
                    && piece.can_capture(cells, fm, to, batyr_caps)
                {
                    let entry = (fm, to, Some(ec));
                    if !captures.contains(&entry) {
                        captures.push(entry);
                    }
                }
            }
        }
    }
    captures
}
