use crate::rules::dict::{dicts, Cells};
use crate::rules::domain::{is_own_color, PieceType};

pub trait Piece: Send + Sync {
    fn color(&self) -> &str;
    fn piece_type(&self) -> PieceType;
    fn can_move(&self, cells: &Cells, from: i32, to: i32) -> bool;
    fn find_enemy_cell_for_capture(&self, cells: &Cells, from: i32, to: i32) -> Option<i32>;
    fn can_capture_impl(&self, cells: &Cells, from: i32, to: i32, caps: &[i32]) -> bool;
    fn can_capture(&self, cells: &Cells, from: i32, to: i32, caps: &[i32]) -> bool {
        if let Some(enemy) = self.find_enemy_cell_for_capture(cells, from, to) {
            if let Some(enemy_piece) = cells.get(&enemy).and_then(|x| x.as_ref()) {
                if is_own_color(enemy_piece, self.color()) {
                    return false;
                }
            }
        }
        self.can_capture_impl(cells, from, to, caps)
    }
}

pub struct Shatra {
    color: String,
}

impl Shatra {
    pub fn new(color: &str) -> Self {
        Self {
            color: color.to_string(),
        }
    }

    fn moves(&self) -> &std::collections::HashMap<i32, Vec<i32>> {
        let d = dicts();
        if self.color == "черный" {
            &d.black_shatra_moves
        } else {
            &d.white_shatra_moves
        }
    }
}

impl Piece for Shatra {
    fn color(&self) -> &str {
        &self.color
    }
    fn piece_type(&self) -> PieceType {
        PieceType::Shatra
    }
    fn find_enemy_cell_for_capture(&self, cells: &Cells, from: i32, to: i32) -> Option<i32> {
        dicts()
            .shatra_biy_captures
            .get(&from)
            .and_then(|m| m.get(&to).copied())
    }
    fn can_move(&self, cells: &Cells, from: i32, to: i32) -> bool {
        if cells.get(&from).and_then(|x| x.as_ref()).is_none() {
            return false;
        }
        if cells.get(&to).and_then(|x| x.as_ref()).is_some() {
            return false;
        }
        if !self.moves().get(&from).map(|v| v.contains(&to)).unwrap_or(false) {
            return false;
        }
        if self.color == "черный" && (1..=9).contains(&from) {
            let mut cell = from + 1;
            while cell < 10 {
                if let Some(p) = cells.get(&cell).and_then(|x| x.as_ref()) {
                    if p.contains("черная шатра") {
                        return false;
                    }
                }
                cell += 1;
            }
        } else if self.color == "белый" && (54..=62).contains(&from) {
            for cell in 54..from {
                if let Some(p) = cells.get(&cell).and_then(|x| x.as_ref()) {
                    if p.contains("белая шатра") {
                        return false;
                    }
                }
            }
        }
        true
    }
    fn can_capture_impl(&self, cells: &Cells, from: i32, to: i32, caps: &[i32]) -> bool {
        let enemy_cell = match self.find_enemy_cell_for_capture(cells, from, to) {
            Some(e) => e,
            None => return false,
        };
        let enemy_piece = match cells.get(&enemy_cell).and_then(|x| x.as_ref()) {
            Some(p) => p,
            None => return false,
        };
        if is_own_color(enemy_piece, &self.color) {
            return false;
        }
        if cells.get(&to).and_then(|x| x.as_ref()).is_some() {
            return false;
        }
        if caps.contains(&enemy_cell) {
            return false;
        }
        if self.color == "черный" && (1..=10).contains(&to) {
            return false;
        }
        if self.color == "белый" && (53..=62).contains(&to) {
            return false;
        }
        true
    }
}

pub struct Biy {
    color: String,
}

impl Biy {
    pub fn new(color: &str) -> Self {
        Self {
            color: color.to_string(),
        }
    }
    fn moves(&self) -> &std::collections::HashMap<i32, Vec<i32>> {
        let d = dicts();
        if self.color == "черный" {
            &d.black_biy_moves
        } else {
            &d.white_biy_moves
        }
    }
}

impl Piece for Biy {
    fn color(&self) -> &str {
        &self.color
    }
    fn piece_type(&self) -> PieceType {
        PieceType::Biy
    }
    fn find_enemy_cell_for_capture(&self, cells: &Cells, from: i32, to: i32) -> Option<i32> {
        dicts()
            .shatra_biy_captures
            .get(&from)
            .and_then(|m| m.get(&to).copied())
    }
    fn can_move(&self, cells: &Cells, from: i32, to: i32) -> bool {
        if cells.get(&from).and_then(|x| x.as_ref()).is_none() {
            return false;
        }
        if cells.get(&to).and_then(|x| x.as_ref()).is_some() {
            return false;
        }
        if !self.moves().get(&from).map(|v| v.contains(&to)).unwrap_or(false) {
            return false;
        }
        self.can_enter_fortress(cells, from, to)
    }
    fn can_capture_impl(&self, cells: &Cells, from: i32, to: i32, _caps: &[i32]) -> bool {
        let enemy_cell = match self.find_enemy_cell_for_capture(cells, from, to) {
            Some(e) => e,
            None => return false,
        };
        let enemy_piece = match cells.get(&enemy_cell).and_then(|x| x.as_ref()) {
            Some(p) => p,
            None => return false,
        };
        if is_own_color(enemy_piece, &self.color) {
            return false;
        }
        if cells.get(&to).and_then(|x| x.as_ref()).is_some() {
            return false;
        }
        self.can_enter_fortress(cells, from, to)
    }
}

impl Biy {
    fn can_enter_fortress(&self, cells: &Cells, _from: i32, to: i32) -> bool {
        if self.color == "черный" && (1..=10).contains(&to) {
            for cell in 1..10 {
                if let Some(p) = cells.get(&cell).and_then(|x| x.as_ref()) {
                    if p.contains("черная шатра") {
                        return false;
                    }
                }
            }
            return true;
        }
        if self.color == "белый" && (53..=62).contains(&to) {
            for cell in 54..63 {
                if let Some(p) = cells.get(&cell).and_then(|x| x.as_ref()) {
                    if p.contains("белая шатра") {
                        return false;
                    }
                }
            }
            return true;
        }
        true
    }
}

pub struct Batyr {
    color: String,
}

impl Batyr {
    pub fn new(color: &str) -> Self {
        Self {
            color: color.to_string(),
        }
    }
}

impl Piece for Batyr {
    fn color(&self) -> &str {
        &self.color
    }
    fn piece_type(&self) -> PieceType {
        PieceType::Batyr
    }
    fn find_enemy_cell_for_capture(&self, cells: &Cells, from: i32, to: i32) -> Option<i32> {
        for dir in dicts().batyr_dirs.get(&from).into_iter().flatten() {
            if !dir.contains(&to) {
                continue;
            }
            for &pos in dir {
                if pos == to {
                    return None;
                }
                if let Some(piece) = cells.get(&pos).and_then(|x| x.as_ref()) {
                    if !is_own_color(piece, &self.color) {
                        return Some(pos);
                    }
                }
            }
        }
        None
    }
    fn can_move(&self, cells: &Cells, from: i32, to: i32) -> bool {
        if cells.get(&from).and_then(|x| x.as_ref()).is_none() {
            return false;
        }
        if cells.get(&to).and_then(|x| x.as_ref()).is_some() {
            return false;
        }
        if self.color == "черный" && (1..=9).contains(&from) && (11..=31).contains(&to) {
            return true;
        }
        if self.color == "белый" && (54..=62).contains(&from) && (32..=52).contains(&to) {
            return true;
        }
        if !self.can_enter_fortress(cells, to) {
            return false;
        }
        self.check_path(cells, from, to, false, &[])
    }
    fn can_capture_impl(&self, cells: &Cells, from: i32, to: i32, caps: &[i32]) -> bool {
        if caps.contains(&to) {
            return false;
        }
        if cells.get(&to).and_then(|x| x.as_ref()).is_some() {
            return false;
        }
        let enemy_cell = match self.find_enemy_cell_for_capture(cells, from, to) {
            Some(e) => e,
            None => return false,
        };
        if caps.contains(&enemy_cell) {
            return false;
        }
        if self.is_entering_own_fortress(to) && self.is_own_shatra_in_fortress(cells) {
            return false;
        }
        self.check_path(cells, from, to, true, caps)
    }
}

impl Batyr {
    fn is_entering_own_fortress(&self, to: i32) -> bool {
        (self.color == "черный" && (1..=10).contains(&to))
            || (self.color == "белый" && (53..=62).contains(&to))
    }
    fn is_own_shatra_in_fortress(&self, cells: &Cells) -> bool {
        if self.color == "черный" {
            for cell in 1..10 {
                if let Some(p) = cells.get(&cell).and_then(|x| x.as_ref()) {
                    if p.contains("черная шатра") {
                        return true;
                    }
                }
            }
        } else {
            for cell in 54..63 {
                if let Some(p) = cells.get(&cell).and_then(|x| x.as_ref()) {
                    if p.contains("белая шатра") {
                        return true;
                    }
                }
            }
        }
        false
    }
    fn can_enter_fortress(&self, cells: &Cells, to: i32) -> bool {
        !(self.is_entering_own_fortress(to) && self.is_own_shatra_in_fortress(cells))
    }
    fn check_path(&self, cells: &Cells, from: i32, to: i32, capture: bool, pending: &[i32]) -> bool {
        for dir in dicts().batyr_dirs.get(&from).into_iter().flatten() {
            let mut pieces_count = 0;
            let mut enemy_cell: Option<i32> = None;
            for &cell in dir {
                if cell == to {
                    if pieces_count == 0 {
                        return !capture && cells.get(&to).and_then(|x| x.as_ref()).is_none();
                    }
                    if pieces_count == 1 && enemy_cell.is_some() {
                        return capture && cells.get(&to).and_then(|x| x.as_ref()).is_none();
                    }
                    return false;
                }
                let content = cells.get(&cell).and_then(|x| x.as_ref());
                let is_pending = pending.contains(&cell);
                if content.is_some() || is_pending {
                    pieces_count += 1;
                    if let Some(p) = content {
                        if !is_own_color(p, &self.color) {
                            enemy_cell = Some(cell);
                        }
                    }
                }
            }
        }
        false
    }
}
