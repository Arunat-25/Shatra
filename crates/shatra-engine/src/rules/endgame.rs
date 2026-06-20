use crate::rules::board::Board;
use crate::rules::dict::Cells;

pub const DRAW_REPETITION: &str = "draw.repetition";
pub const DRAW_TWO_BIYS: &str = "draw.two_biys";

pub struct GameEnd {
    pub over: bool,
    pub winner_color: Option<String>,
    pub draw_reason: Option<String>,
}

fn only_two_biys_left(board: &Board) -> bool {
    let mut biy = 0;
    let mut other = 0;
    for name in board.cells.values().flatten() {
        if name.contains("бий") {
            biy += 1;
        } else {
            other += 1;
        }
    }
    biy == 2 && other == 0
}

pub fn is_game_over(
    board: &Board,
    position_history: Option<&std::collections::HashMap<String, i32>>,
    moves_with_two_biys: i32,
) -> GameEnd {
    let mut biy_count = 0;
    let mut last_biy_color: Option<String> = None;
    for name in board.cells.values().flatten() {
        if name.contains("бий") {
            biy_count += 1;
            last_biy_color = Some(if name.contains("бел") {
                "белый".into()
            } else {
                "черный".into()
            });
        }
    }
    if biy_count == 1 {
        return GameEnd {
            over: true,
            winner_color: last_biy_color,
            draw_reason: None,
        };
    }
    if biy_count == 2 && moves_with_two_biys >= 3 && only_two_biys_left(board) {
        return GameEnd {
            over: true,
            winner_color: None,
            draw_reason: Some(DRAW_TWO_BIYS.into()),
        };
    }
    if let Some(hist) = position_history {
        let pos_key = position_key(&board.cells);
        if hist.get(&pos_key).copied().unwrap_or(0) >= 3 {
            return GameEnd {
                over: true,
                winner_color: None,
                draw_reason: Some(DRAW_REPETITION.into()),
            };
        }
    }
    GameEnd {
        over: false,
        winner_color: None,
        draw_reason: None,
    }
}

pub fn record_position(history: &mut std::collections::HashMap<String, i32>, positions: &Cells) {
    let key = position_key(positions);
    *history.entry(key).or_insert(0) += 1;
}

fn position_key(cells: &Cells) -> String {
    let mut entries: Vec<(i32, Option<String>)> = cells.iter().map(|(k, v)| (*k, v.clone())).collect();
    entries.sort_by_key(|(k, _)| *k);
    serde_json::to_string(&entries).unwrap_or_default()
}
