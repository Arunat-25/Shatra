use std::collections::HashSet;
use std::sync::OnceLock;

use crate::rules::dict::Cells;

pub const SIDE_FILE_CELLS: &[i32] = &[
    11, 18, 25, 32, 39, 46, 17, 24, 31, 38, 45, 52,
];
pub const DANGER_ZONE_CELLS: &[i32] = &[27, 28, 29, 34, 35, 36];
pub const BLACK_BIY_ANCHOR: &[i32] = &[11, 17, 7, 9];
pub const WHITE_BIY_ANCHOR: &[i32] = &[46, 52, 54, 56];
pub const BLACK_BATYR_ANCHOR: &[i32] = &[2, 5, 8, 10, 13, 14, 15];
pub const WHITE_BATYR_ANCHOR: &[i32] = &[48, 49, 50, 53, 55, 58, 61];
pub const MAIN_FIELD_CELLS: std::ops::RangeInclusive<i32> = 11..=52;
pub const WHITE_FORTRESS_CELLS: std::ops::RangeInclusive<i32> = 54..=62;
pub const BLACK_FORTRESS_CELLS: std::ops::RangeInclusive<i32> = 1..=9;
pub const WHITE_GATE: i32 = 53;
pub const BLACK_GATE: i32 = 10;
pub const BIY_ANCHOR_SPARSE_FACTOR: f64 = 0.35;
pub const OPPONENT_MASS_THRESHOLD: i32 = 6;

fn side_file_set() -> &'static HashSet<i32> {
    static SET: OnceLock<HashSet<i32>> = OnceLock::new();
    SET.get_or_init(|| SIDE_FILE_CELLS.iter().copied().collect())
}

fn danger_zone_set() -> &'static HashSet<i32> {
    static SET: OnceLock<HashSet<i32>> = OnceLock::new();
    SET.get_or_init(|| DANGER_ZONE_CELLS.iter().copied().collect())
}

pub fn is_main_field_cell(cell: i32) -> bool {
    MAIN_FIELD_CELLS.contains(&cell)
}

pub fn own_fortress_cells(color: &str) -> Vec<i32> {
    if color == "белый" {
        (54..=62).chain(std::iter::once(WHITE_GATE)).collect()
    } else {
        (1..=9).chain(std::iter::once(BLACK_GATE)).collect()
    }
}

pub fn count_own_pieces_in_fortress(cells: &Cells, color: &str) -> i32 {
    own_fortress_cells(color)
        .iter()
        .filter(|&&cell| {
            cells
                .get(&cell)
                .and_then(|x| x.as_ref())
                .map(|n| piece_color_from_name(n) == color)
                .unwrap_or(false)
        })
        .count() as i32
}

pub fn count_opponent_shatras_in_own_fortress(cells: &Cells, ai_color: &str) -> i32 {
    let opp = if ai_color == "белый" {
        "черный"
    } else {
        "белый"
    };
    own_fortress_cells(ai_color)
        .iter()
        .filter(|&&cell| {
            cells
                .get(&cell)
                .and_then(|x| x.as_ref())
                .map(|n| piece_color_from_name(n) == opp && safe_piece_type(n) == "шатра")
                .unwrap_or(false)
        })
        .count() as i32
}

pub fn is_fortress_entry(_from_cell: i32, to_cell: i32, color: &str) -> bool {
    if color == "белый" {
        BLACK_FORTRESS_CELLS.contains(&to_cell) || to_cell == BLACK_GATE
    } else {
        WHITE_FORTRESS_CELLS.contains(&to_cell) || to_cell == WHITE_GATE
    }
}

pub fn is_fortress_shatra_deploy(from_cell: i32, to_cell: i32, color: &str) -> bool {
    if !is_main_field_cell(to_cell) {
        return false;
    }
    if color == "белый" {
        WHITE_FORTRESS_CELLS.contains(&from_cell)
    } else {
        BLACK_FORTRESS_CELLS.contains(&from_cell)
    }
}

pub fn is_biy_deploy_to_main_field(from_cell: i32, to_cell: i32, color: &str) -> bool {
    if !is_main_field_cell(to_cell) {
        return false;
    }
    if color == "белый" {
        from_cell == WHITE_GATE || WHITE_FORTRESS_CELLS.contains(&from_cell)
    } else {
        from_cell == BLACK_GATE || BLACK_FORTRESS_CELLS.contains(&from_cell)
    }
}

pub fn biy_anchor_cells(color: &str) -> &'static [i32] {
    if color == "черный" {
        BLACK_BIY_ANCHOR
    } else {
        WHITE_BIY_ANCHOR
    }
}

pub fn batyr_anchor_cells(color: &str) -> &'static [i32] {
    if color == "черный" {
        BLACK_BATYR_ANCHOR
    } else {
        WHITE_BATYR_ANCHOR
    }
}

pub fn piece_color_from_name(name: &str) -> &str {
    if name.contains("бел") {
        "белый"
    } else {
        "черный"
    }
}

pub fn safe_piece_type(name: &str) -> &str {
    name.split_whitespace().last().unwrap_or("")
}

pub fn main_field_density(cells: &Cells) -> i32 {
    (11..=52)
        .filter(|c| cells.get(c).and_then(|x| x.as_ref()).is_some())
        .count() as i32
}

pub fn biy_anchor_factor(density: i32, crowded_threshold: i32) -> f64 {
    if density >= crowded_threshold {
        1.0
    } else {
        BIY_ANCHOR_SPARSE_FACTOR
    }
}

pub fn in_side_file(cell: i32) -> bool {
    side_file_set().contains(&cell)
}

pub fn in_danger_zone(cell: i32) -> bool {
    danger_zone_set().contains(&cell)
}

pub fn in_slice(cells: &[i32], cell: i32) -> bool {
    cells.contains(&cell)
}
