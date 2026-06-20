use std::collections::HashMap;

use crate::rules::board::Board;
use crate::rules::dict::{dicts, Cells};
use crate::rules::domain::{opponent, PieceType};
use crate::rules::endgame::{is_game_over, record_position};
use crate::rules::hints::{
    batyr_can_continue_capture, find_captured_enemy, get_all_mandatory_captures, validate_move,
};
use crate::rules::message_codes::{
    validation_to_message, CAPTURE_CONTINUE, CAPTURE_CONTINUE_SAME, CAPTURE_MUST,
    CAPTURE_MUST_CONTINUE, MOVE_PASSED, MOVE_UNKNOWN_PIECE, PIECE_PROMOTED, TURN_NOW,
};

const PROMOTION_WHITE: [i32; 3] = [1, 2, 3];
const PROMOTION_BLACK: [i32; 3] = [60, 61, 62];

#[derive(Debug, Clone)]
pub struct ProcessMoveResult {
    pub message_code: String,
    pub movers_color: Option<String>,
    pub game_over: bool,
    pub winner_color: Option<String>,
    pub draw_reason: Option<String>,
    pub updated_positions: Option<Cells>,
    pub captured_positions: Vec<i32>,
    pub captured_pieces: Vec<i32>,
    pub position_for_mandatory_capture: Option<i32>,
    pub opportunity_pass_the_move: bool,
}

fn clone_cells(cells: &Cells) -> Cells {
    cells.clone()
}

fn promote_shatra(cells: &mut Cells, cell: i32, color: &str) -> bool {
    let name = match cells.get(&cell).and_then(|x| x.as_ref()) {
        Some(n) => n.clone(),
        None => return false,
    };
    if !name.contains("шатра") {
        return false;
    }
    if color == "белый" && PROMOTION_WHITE.contains(&cell) {
        cells.insert(cell, Some("белый батыр".into()));
        return true;
    }
    if color == "черный" && PROMOTION_BLACK.contains(&cell) {
        cells.insert(cell, Some("черный батыр".into()));
        return true;
    }
    false
}

fn execute_move(
    cells: &Cells,
    from: i32,
    to: i32,
    color: &str,
    batyr_caps: &[i32],
) -> (Cells, Vec<i32>, Vec<i32>) {
    let mut new_cells = clone_cells(cells);
    let mut board = Board::new(new_cells.clone());
    let mut captured_positions = Vec::new();
    let mut new_batyr = batyr_caps.to_vec();
    let piece = board.piece_at(from).unwrap();
    if piece.can_capture(cells, from, to, batyr_caps) {
        let enemy = find_captured_enemy(cells, piece.as_ref(), from, to, batyr_caps);
        board.move_piece(from, to);
        new_cells = board.copy_cells();
        if let Some(enemy_cell) = enemy {
            board.remove_piece(enemy_cell);
            new_cells = board.copy_cells();
            captured_positions.push(enemy_cell);
            if piece.piece_type() == PieceType::Batyr {
                new_batyr.push(enemy_cell);
            }
        }
        return (new_cells, captured_positions, new_batyr);
    }
    board.move_piece(from, to);
    new_cells = board.copy_cells();
    if piece.piece_type() == PieceType::Batyr {
        new_batyr.clear();
    }
    (new_cells, captured_positions, new_batyr)
}

fn chain_capture_after_turn(board: &Board, next: &str) -> Option<i32> {
    let mandatory = get_all_mandatory_captures(board, next, &[]);
    if mandatory.is_empty() {
        return None;
    }
    let has_non_biy = mandatory.iter().any(|(f, _)| {
        board
            .piece_at(*f)
            .map(|p| p.piece_type() != PieceType::Biy)
            .unwrap_or(false)
    });
    if !has_non_biy {
        return None;
    }
    Some(mandatory[0].0)
}

fn finish_move(
    positions: Cells,
    mover: &str,
    message_code: &str,
    captured_positions: Vec<i32>,
    game_over: bool,
    winner: Option<String>,
    draw: Option<String>,
    opportunity_pass: bool,
    mandatory: Option<i32>,
    captured_pieces: Vec<i32>,
) -> ProcessMoveResult {
    ProcessMoveResult {
        message_code: message_code.to_string(),
        movers_color: Some(opponent(mover)),
        game_over,
        winner_color: winner,
        draw_reason: draw,
        updated_positions: Some(positions),
        captured_positions,
        captured_pieces,
        position_for_mandatory_capture: mandatory,
        opportunity_pass_the_move: opportunity_pass,
    }
}

pub fn process_move(
    cells: &Cells,
    current_color: &str,
    from_cell: i32,
    to_cell: i32,
    chain_capture_cell: Option<i32>,
    batyr_captured: &[i32],
    position_history: &mut HashMap<String, i32>,
    moves_with_two_biys: i32,
) -> ProcessMoveResult {
    let mut caps = batyr_captured.to_vec();
    let board_copy = clone_cells(cells);

    let end = is_game_over(&Board::new(board_copy.clone()), Some(position_history), moves_with_two_biys);
    if end.over {
        return ProcessMoveResult {
            message_code: String::new(),
            movers_color: None,
            game_over: true,
            winner_color: end.winner_color,
            draw_reason: end.draw_reason,
            updated_positions: Some(cells.clone()),
            captured_positions: vec![],
            captured_pieces: vec![],
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }

    if chain_capture_cell == Some(0) {
        let end2 = is_game_over(&Board::new(board_copy.clone()), Some(position_history), moves_with_two_biys);
        return finish_move(
            board_copy,
            current_color,
            MOVE_PASSED,
            vec![],
            end2.over,
            end2.winner_color,
            end2.draw_reason,
            false,
            None,
            vec![],
        );
    }

    if let Some(chain) = chain_capture_cell {
        if chain != 0 {
            return process_chain(
                &board_copy,
                cells,
                current_color,
                from_cell,
                to_cell,
                chain,
                &caps,
                position_history,
                moves_with_two_biys,
            );
        }
    }

    let v = validate_move(&board_copy, from_cell, to_cell, current_color, &caps, true, None);
    if !v.valid {
        return ProcessMoveResult {
            message_code: validation_to_message(&v.code).to_string(),
            movers_color: None,
            game_over: false,
            winner_color: None,
            draw_reason: None,
            updated_positions: None,
            captured_positions: vec![],
            captured_pieces: vec![],
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }

    let (mut new_cells, captured_positions, new_batyr) =
        execute_move(&board_copy, from_cell, to_cell, current_color, &caps);
    caps = new_batyr;

    let board_before = Board::new(board_copy);
    let mut piece = board_before.piece_at(from_cell);
    if piece.is_none() {
        piece = board_before.piece_at(to_cell);
    }
    let mut piece_kind = piece.as_ref().map(|p| p.piece_type());

    if piece_kind == Some(PieceType::Shatra) {
        if promote_shatra(&mut new_cells, to_cell, current_color) {
            if captured_positions.is_empty() {
                return finish_move(
                    new_cells,
                    current_color,
                    PIECE_PROMOTED,
                    captured_positions,
                    false,
                    None,
                    None,
                    false,
                    None,
                    vec![],
                );
            }
            piece_kind = Some(PieceType::Batyr);
        }
    }

    let mut end = is_game_over(&Board::new(new_cells.clone()), Some(position_history), moves_with_two_biys);
    if end.over {
        return ProcessMoveResult {
            message_code: String::new(),
            movers_color: None,
            game_over: true,
            winner_color: end.winner_color.clone(),
            draw_reason: end.draw_reason.clone(),
            updated_positions: Some(new_cells),
            captured_positions,
            captured_pieces: caps,
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }

    let has_captured = !captured_positions.is_empty();
    let mut can_continue = false;
    if has_captured {
        if matches!(piece_kind, Some(PieceType::Shatra) | Some(PieceType::Biy)) {
            let board = Board::new(new_cells.clone());
            if let Some(p) = board.piece_at(to_cell) {
                if let Some(targets) = dicts().shatra_biy_captures.get(&to_cell) {
                    for &next in targets.keys() {
                        if p.can_capture(&new_cells, to_cell, next, &caps) {
                            can_continue = true;
                            break;
                        }
                    }
                }
            }
        } else {
            can_continue = batyr_can_continue_capture(&Board::new(new_cells.clone()), to_cell, current_color, &caps);
        }
    }

    let can_pass = piece_kind == Some(PieceType::Biy) && can_continue;
    if can_continue {
        return ProcessMoveResult {
            message_code: CAPTURE_CONTINUE.into(),
            movers_color: Some(current_color.into()),
            game_over: false,
            winner_color: None,
            draw_reason: None,
            updated_positions: Some(new_cells),
            captured_positions,
            captured_pieces: caps,
            position_for_mandatory_capture: Some(to_cell),
            opportunity_pass_the_move: can_pass,
        };
    }

    if has_captured && !can_continue {
        let next = opponent(current_color);
        end = is_game_over(&Board::new(new_cells.clone()), Some(position_history), moves_with_two_biys);
        record_position(position_history, &new_cells);
        return finish_move(
            new_cells,
            current_color,
            TURN_NOW,
            captured_positions,
            end.over,
            end.winner_color,
            end.draw_reason,
            can_pass,
            None,
            caps,
        );
    }

    let next = opponent(current_color);
    end = is_game_over(&Board::new(new_cells.clone()), Some(position_history), moves_with_two_biys);
    let chain_pos = if !end.over {
        chain_capture_after_turn(&Board::new(new_cells.clone()), &next)
    } else {
        None
    };
    record_position(position_history, &new_cells);
    finish_move(
        new_cells,
        current_color,
        TURN_NOW,
        captured_positions,
        end.over,
        end.winner_color,
        end.draw_reason,
        can_pass,
        chain_pos,
        caps,
    )
}

fn process_chain(
    board_copy: &Cells,
    cells: &Cells,
    color: &str,
    from: i32,
    to: i32,
    chain: i32,
    caps: &[i32],
    history: &mut HashMap<String, i32>,
    moves_with_two_biys: i32,
) -> ProcessMoveResult {
    if from != chain {
        return ProcessMoveResult {
            message_code: CAPTURE_CONTINUE_SAME.into(),
            movers_color: Some(color.into()),
            game_over: false,
            winner_color: None,
            draw_reason: None,
            updated_positions: Some(cells.clone()),
            captured_positions: vec![],
            captured_pieces: caps.to_vec(),
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }
    let board = Board::new(board_copy.clone());
    let piece = board.piece_at(from);
    if piece.is_none() {
        return ProcessMoveResult {
            message_code: MOVE_UNKNOWN_PIECE.into(),
            movers_color: Some(color.into()),
            game_over: false,
            winner_color: None,
            draw_reason: None,
            updated_positions: Some(cells.clone()),
            captured_positions: vec![],
            captured_pieces: vec![],
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }
    let p = piece.unwrap();
    match p.piece_type() {
        PieceType::Shatra | PieceType::Biy => {
            process_chain_shatra_biy(board_copy, cells, color, from, to, caps, p.as_ref(), history, moves_with_two_biys)
        }
        PieceType::Batyr => {
            process_chain_batyr(board_copy, cells, color, from, to, caps, p.as_ref(), history, moves_with_two_biys)
        }
    }
}

fn process_chain_shatra_biy(
    board_copy: &Cells,
    cells: &Cells,
    color: &str,
    from: i32,
    to: i32,
    caps: &[i32],
    piece: &dyn crate::rules::pieces::Piece,
    history: &mut HashMap<String, i32>,
    moves_with_two_biys: i32,
) -> ProcessMoveResult {
    if !piece.can_capture(board_copy, from, to, caps) {
        return ProcessMoveResult {
            message_code: CAPTURE_MUST.into(),
            movers_color: Some(color.into()),
            game_over: false,
            winner_color: None,
            draw_reason: None,
            updated_positions: Some(cells.clone()),
            captured_positions: vec![],
            captured_pieces: caps.to_vec(),
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }
    let (mut new_cells, captured, new_caps) = execute_move(board_copy, from, to, color, caps);
    promote_shatra(&mut new_cells, to, color);
    let end = is_game_over(&Board::new(new_cells.clone()), Some(history), moves_with_two_biys);
    if end.over {
        return ProcessMoveResult {
            message_code: String::new(),
            movers_color: None,
            game_over: true,
            winner_color: end.winner_color,
            draw_reason: end.draw_reason,
            updated_positions: Some(new_cells),
            captured_positions: captured,
            captured_pieces: new_caps,
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }
    let board = Board::new(new_cells.clone());
    let mut can_continue = false;
    if let Some(p) = board.piece_at(to) {
        if let Some(targets) = dicts().shatra_biy_captures.get(&to) {
            for &n in targets.keys() {
                if p.can_capture(&new_cells, to, n, &new_caps) {
                    can_continue = true;
                    break;
                }
            }
        }
    }
    let piece_kind = piece.piece_type();
    let can_pass = piece_kind == PieceType::Biy && can_continue;
    if can_continue {
        return ProcessMoveResult {
            message_code: CAPTURE_CONTINUE.into(),
            movers_color: Some(color.into()),
            game_over: false,
            winner_color: None,
            draw_reason: None,
            updated_positions: Some(new_cells),
            captured_positions: captured,
            captured_pieces: new_caps,
            position_for_mandatory_capture: Some(to),
            opportunity_pass_the_move: can_pass,
        };
    }
    finish_move(new_cells, color, TURN_NOW, captured, false, None, None, can_pass, None, new_caps)
}

fn process_chain_batyr(
    board_copy: &Cells,
    cells: &Cells,
    color: &str,
    from: i32,
    to: i32,
    caps: &[i32],
    piece: &dyn crate::rules::pieces::Piece,
    history: &mut HashMap<String, i32>,
    moves_with_two_biys: i32,
) -> ProcessMoveResult {
    if !piece.can_capture(board_copy, from, to, caps) {
        return ProcessMoveResult {
            message_code: CAPTURE_MUST_CONTINUE.into(),
            movers_color: Some(color.into()),
            game_over: false,
            winner_color: None,
            draw_reason: None,
            updated_positions: Some(cells.clone()),
            captured_positions: vec![],
            captured_pieces: caps.to_vec(),
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }
    let (new_cells, captured, new_caps) = execute_move(board_copy, from, to, color, caps);
    let end = is_game_over(&Board::new(new_cells.clone()), Some(history), moves_with_two_biys);
    if end.over {
        return ProcessMoveResult {
            message_code: String::new(),
            movers_color: None,
            game_over: true,
            winner_color: end.winner_color,
            draw_reason: end.draw_reason,
            updated_positions: Some(new_cells),
            captured_positions: captured,
            captured_pieces: new_caps,
            position_for_mandatory_capture: None,
            opportunity_pass_the_move: false,
        };
    }
    let can_continue = batyr_can_continue_capture(&Board::new(new_cells.clone()), to, color, &new_caps);
    if can_continue {
        return ProcessMoveResult {
            message_code: CAPTURE_CONTINUE.into(),
            movers_color: Some(color.into()),
            game_over: false,
            winner_color: None,
            draw_reason: None,
            updated_positions: Some(new_cells),
            captured_positions: captured,
            captured_pieces: new_caps,
            position_for_mandatory_capture: Some(to),
            opportunity_pass_the_move: false,
        };
    }
    finish_move(new_cells, color, TURN_NOW, captured, false, None, None, false, None, new_caps)
}
