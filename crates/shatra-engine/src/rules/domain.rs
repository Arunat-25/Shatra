#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PieceType {
    Shatra,
    Biy,
    Batyr,
}

pub fn is_own_color(piece_name: &str, color: &str) -> bool {
    if piece_name.contains("бел") {
        return color.starts_with("бел");
    }
    color.starts_with("чер")
}

pub fn parse_piece_name(name: &str) -> Option<(String, PieceType)> {
    if name.is_empty() {
        return None;
    }
    let color = if name.contains("бел") {
        "белый".to_string()
    } else {
        "черный".to_string()
    };
    let piece_type = if name.contains("шатра") {
        PieceType::Shatra
    } else if name.contains("бий") {
        PieceType::Biy
    } else {
        PieceType::Batyr
    };
    Some((color, piece_type))
}

pub fn opponent(color: &str) -> String {
    if color == "белый" {
        "черный".to_string()
    } else {
        "белый".to_string()
    }
}
