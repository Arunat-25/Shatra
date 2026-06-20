use std::collections::HashMap;

use crate::rules::dict::Cells;
use crate::rules::domain::{parse_piece_name, PieceType};
use crate::rules::pieces::{Batyr, Biy, Piece, Shatra};

pub struct Board {
    pub cells: Cells,
}

impl Board {
    pub fn new(cells: Cells) -> Self {
        Self { cells }
    }

    pub fn from_str_map(cells: &HashMap<i32, String>) -> Self {
        Self::new(crate::rules::dict::normalize_cells(cells))
    }

    pub fn piece_at(&self, cell: i32) -> Option<Box<dyn Piece>> {
        let name = self.cells.get(&cell)?.as_ref()?;
        let (_, pt) = parse_piece_name(name)?;
        let color = if name.contains("бел") {
            "белый"
        } else {
            "черный"
        };
        Some(match pt {
            PieceType::Shatra => Box::new(Shatra::new(color)),
            PieceType::Biy => Box::new(Biy::new(color)),
            PieceType::Batyr => Box::new(Batyr::new(color)),
        })
    }

    pub fn all_pieces(&self) -> Vec<(i32, String)> {
        let mut out = Vec::new();
        for (cell, name) in &self.cells {
            if name.is_some() {
                out.push((*cell, name.clone().unwrap()));
            }
        }
        out
    }

    pub fn move_piece(&mut self, from: i32, to: i32) {
        let piece = self.cells.get(&from).cloned().flatten();
        self.cells.insert(to, piece);
        self.cells.insert(from, None);
    }

    pub fn remove_piece(&mut self, cell: i32) {
        self.cells.insert(cell, None);
    }

    pub fn copy_cells(&self) -> Cells {
        self.cells.clone()
    }
}
