use crate::rules::board::Board;
use crate::rules::dict::{dicts, Cells};
use crate::rules::domain::PieceType;
use crate::rules::pieces::{Batyr, Biy, Piece, Shatra};

pub struct ValidationResult {
    pub valid: bool,
    pub code: String,
}

pub struct HintsResult {
    pub essential_positions: Vec<i32>,
    pub captured_pieces: Vec<i32>,
    pub message_code: String,
}

pub fn get_all_mandatory_captures(board: &Board, color: &str, batyr_caps: &[i32]) -> Vec<(i32, i32)> {
    let mut mandatory = Vec::new();
    for (pos, name) in board.all_pieces() {
        let piece = match board.piece_at(pos) {
            Some(p) => p,
            None => continue,
        };
        if piece.color() != color {
            continue;
        }
        let mut candidates = Vec::new();
        match piece.piece_type() {
            PieceType::Shatra | PieceType::Biy => {
                if let Some(caps) = dicts().shatra_biy_captures.get(&pos) {
                    candidates.extend(caps.keys().copied());
                }
            }
            PieceType::Batyr => {
                if let Some(dirs) = dicts().batyr_dirs.get(&pos) {
                    for dir in dirs {
                        candidates.extend(dir.iter().copied());
                    }
                }
            }
        }
        candidates.sort_unstable();
        candidates.dedup();
        for to_cell in candidates {
            if piece.can_capture(&board.cells, pos, to_cell, batyr_caps) {
                mandatory.push((pos, to_cell));
            }
        }
    }
    mandatory
}

pub fn validate_move(
    cells: &Cells,
    from: i32,
    to: i32,
    current_color: &str,
    batyr_caps: &[i32],
    check_mandatory: bool,
    _chain_cell: Option<i32>,
) -> ValidationResult {
    let board = Board::new(cells.clone());
    let piece = match board.piece_at(from) {
        Some(p) => p,
        None => {
            return ValidationResult {
                valid: false,
                code: "NO_PIECE".into(),
            }
        }
    };
    if piece.color() != current_color {
        return ValidationResult {
            valid: false,
            code: "WRONG_COLOR".into(),
        };
    }
    if cells.get(&to).and_then(|x| x.as_ref()).is_some() {
        return ValidationResult {
            valid: false,
            code: "TARGET_OCCUPIED".into(),
        };
    }
    if check_mandatory {
        let mandatory = get_all_mandatory_captures(&board, current_color, batyr_caps);
        if !mandatory.is_empty() {
            let has_non_biy = mandatory.iter().any(|(f, _)| {
                board
                    .piece_at(*f)
                    .map(|p| p.piece_type() != PieceType::Biy)
                    .unwrap_or(false)
            });
            let attackers: std::collections::HashSet<i32> = mandatory.iter().map(|(f, _)| *f).collect();
            if !attackers.contains(&from) {
                if has_non_biy {
                    return ValidationResult {
                        valid: false,
                        code: "MANDATORY_CAPTURE_OTHER_PIECE".into(),
                    };
                }
                if piece.piece_type() != PieceType::Biy {
                    return ValidationResult {
                        valid: false,
                        code: "ONLY_BIY_CAN_CAPTURE".into(),
                    };
                }
            } else {
                let capture_targets: std::collections::HashSet<i32> =
                    mandatory.iter().filter(|(f, _)| *f == from).map(|(_, t)| *t).collect();
                if !capture_targets.contains(&to) {
                    if !(piece.piece_type() == PieceType::Biy && !has_non_biy) {
                        return ValidationResult {
                            valid: false,
                            code: "MANDATORY_CAPTURE_THIS_PIECE".into(),
                        };
                    }
                }
            }
        }
    }
    let piece2 = board.piece_at(from).unwrap();
    if piece2.piece_type() == PieceType::Batyr {
        for dir in dicts().batyr_dirs.get(&from).into_iter().flatten() {
            if !dir.contains(&to) {
                continue;
            }
            for &cell in dir {
                if cell == to {
                    break;
                }
                if let Some(p) = cells.get(&cell).and_then(|x| x.as_ref()) {
                    if p.contains(current_color) {
                        return ValidationResult {
                            valid: false,
                            code: "OWN_PIECE_BLOCKS_BATYR".into(),
                        };
                    }
                }
            }
        }
    }
    if piece2.can_capture(cells, from, to, batyr_caps) {
        return ValidationResult {
            valid: true,
            code: "OK_CAPTURE".into(),
        };
    }
    if piece2.can_move(cells, from, to) {
        return ValidationResult {
            valid: true,
            code: "OK_MOVE".into(),
        };
    }
    ValidationResult {
        valid: false,
        code: "ILLEGAL_MOVE".into(),
    }
}

pub fn find_captured_enemy(
    cells: &Cells,
    piece: &dyn Piece,
    from: i32,
    to: i32,
    batyr_caps: &[i32],
) -> Option<i32> {
    if piece.piece_type() == PieceType::Shatra || piece.piece_type() == PieceType::Biy {
        return dicts()
            .shatra_biy_captures
            .get(&from)
            .and_then(|m| m.get(&to).copied());
    }
    if piece.piece_type() == PieceType::Batyr {
        let opp_prefix = if piece.color() == "белый" { "чер" } else { "бел" };
        for dir in dicts().batyr_dirs.get(&from).into_iter().flatten() {
            if !dir.contains(&to) {
                continue;
            }
            for &pos in dir {
                if pos == to {
                    return None;
                }
                if let Some(content) = cells.get(&pos).and_then(|x| x.as_ref()) {
                    if content.contains(opp_prefix) {
                        if !batyr_caps.contains(&pos) {
                            return Some(pos);
                        }
                    } else {
                        return None;
                    }
                }
            }
        }
    }
    None
}

pub fn batyr_can_continue_capture(board: &Board, from: i32, color: &str, caps: &[i32]) -> bool {
    let piece = match board.piece_at(from) {
        Some(p) => p,
        None => return false,
    };
    if piece.piece_type() != PieceType::Batyr {
        return false;
    }
    for (start, target) in get_all_mandatory_captures(board, color, caps) {
        if start == from && piece.can_capture(&board.cells, from, target, caps) {
            return true;
        }
    }
    false
}

fn all_candidates(cells: &Cells, color: &str, from: i32, pt: PieceType) -> Vec<i32> {
    let mut candidates = Vec::new();
    let d = dicts();
    match pt {
        PieceType::Shatra => {
            let moves = if color == "черный" {
                &d.black_shatra_moves
            } else {
                &d.white_shatra_moves
            };
            if let Some(v) = moves.get(&from) {
                candidates.extend(v.iter().copied());
            }
            if let Some(caps) = d.shatra_biy_captures.get(&from) {
                candidates.extend(caps.keys().copied());
            }
        }
        PieceType::Biy => {
            let moves = if color == "черный" {
                &d.black_biy_moves
            } else {
                &d.white_biy_moves
            };
            if let Some(v) = moves.get(&from) {
                candidates.extend(v.iter().copied());
            }
            if let Some(caps) = d.shatra_biy_captures.get(&from) {
                candidates.extend(caps.keys().copied());
            }
        }
        PieceType::Batyr => {
            if let Some(dirs) = d.batyr_dirs.get(&from) {
                for dir in dirs {
                    candidates.extend(dir.iter().copied());
                }
            }
        }
    }
    candidates
}

pub fn get_hints(
    cells: &Cells,
    current_color: &str,
    from_cell: i32,
    batyr_captured: &[i32],
    chain_capture_cell: Option<i32>,
) -> HintsResult {
    let caps = batyr_captured.to_vec();
    let board = Board::new(cells.clone());
    let piece = match board.piece_at(from_cell) {
        Some(p) => p,
        None => {
            return HintsResult {
                essential_positions: vec![],
                captured_pieces: caps,
                message_code: String::new(),
            }
        }
    };
    if piece.color() != current_color {
        return HintsResult {
            essential_positions: vec![],
            captured_pieces: caps,
            message_code: String::new(),
        };
    }
    if let Some(chain) = chain_capture_cell {
        if chain != 0 && from_cell != chain {
            return HintsResult {
                essential_positions: vec![],
                captured_pieces: caps,
                message_code: "capture.continue_same".into(),
            };
        }
        let allowed = chain_hints(cells, from_cell, &caps, piece.as_ref());
        return HintsResult {
            essential_positions: allowed.clone(),
            captured_pieces: caps,
            message_code: String::new(),
        };
    }
    let candidates = all_candidates(cells, current_color, from_cell, piece.piece_type());
    let mut allowed = Vec::new();
    for target in candidates {
        let v = validate_move(cells, from_cell, target, current_color, &caps, true, None);
        if v.valid {
            allowed.push(target);
        }
    }
    HintsResult {
        essential_positions: allowed,
        captured_pieces: caps,
        message_code: String::new(),
    }
}

fn chain_hints(cells: &Cells, from: i32, caps: &[i32], piece: &dyn Piece) -> Vec<i32> {
    let mut allowed = Vec::new();
    match piece.piece_type() {
        PieceType::Shatra | PieceType::Biy => {
            if let Some(targets) = dicts().shatra_biy_captures.get(&from) {
                for &to in targets.keys() {
                    if piece.can_capture(cells, from, to, caps) {
                        allowed.push(to);
                    }
                }
            }
        }
        PieceType::Batyr => {
            if let Some(dirs) = dicts().batyr_dirs.get(&from) {
                for dir in dirs {
                    for &to in dir {
                        if piece.can_capture(cells, from, to, caps) {
                            allowed.push(to);
                        }
                    }
                }
            }
        }
    }
    allowed
}
