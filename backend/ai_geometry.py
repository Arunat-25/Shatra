"""Board geometry for AI strategic bonuses (side files, biy anchors)."""
from __future__ import annotations

# Крайние вертикали большого поля (профессиональное продвижение по флангам).
SIDE_FILE_CELLS = frozenset({11, 18, 25, 32, 39, 46, 17, 24, 31, 38, 45, 52})

# Опасная центральная полоса — не держать здесь фигуры без нужды.
DANGER_ZONE_CELLS = frozenset({27, 28, 29, 34, 35, 36})

BLACK_BIY_ANCHOR = frozenset({11, 17, 7, 9})
WHITE_BIY_ANCHOR = frozenset({46, 52, 54, 56})

# Сильные клетки крепости для батыра (фланг / ворота).
BLACK_BATYR_ANCHOR = frozenset({2, 5, 8, 10, 13, 14, 15})
WHITE_BATYR_ANCHOR = frozenset({48, 49, 50, 53, 55, 58, 61})

MAIN_FIELD_CELLS = frozenset(range(11, 53))

WHITE_FORTRESS_CELLS = frozenset(range(54, 63))
BLACK_FORTRESS_CELLS = frozenset(range(1, 10))
WHITE_GATE = 53
BLACK_GATE = 10

BIY_ANCHOR_SPARSE_FACTOR = 0.35

# Бонусы/штрафы за боковые и опасные клетки — когда у соперника >6 фигур на доске (всего).
OPPONENT_MASS_THRESHOLD = 6


def is_main_field_cell(cell: int) -> bool:
    return cell in MAIN_FIELD_CELLS


def own_fortress_cells(color: str) -> frozenset[int]:
    """Своя крепость + ворота (клетки 1–10 для чёрных, 53–62 для белых)."""
    if color == "белый":
        return WHITE_FORTRESS_CELLS | frozenset({WHITE_GATE})
    return BLACK_FORTRESS_CELLS | frozenset({BLACK_GATE})


def count_own_pieces_in_fortress(cells: dict, color: str) -> int:
    zone = own_fortress_cells(color)
    return sum(
        1
        for cell in zone
        if (name := piece_name_at(cells, cell)) and piece_color_from_name(name) == color
    )


def count_opponent_shatras_in_own_fortress(cells: dict, ai_color: str) -> int:
    """Шатры соперника в крепости ИИ (без своих фигур в крепости — см. evaluate)."""
    opp = "черный" if ai_color == "белый" else "белый"
    zone = own_fortress_cells(ai_color)
    total = 0
    for cell in zone:
        name = piece_name_at(cells, cell)
        if not name or piece_color_from_name(name) != opp:
            continue
        if name.split()[-1] == "шатра":
            total += 1
    return total


def is_fortress_entry(from_cell: int, to_cell: int, color: str) -> bool:
    """Заход в крепость соперника (ворота или клетки крепости)."""
    if color == "белый":
        return to_cell in BLACK_FORTRESS_CELLS or to_cell == BLACK_GATE
    return to_cell in WHITE_FORTRESS_CELLS or to_cell == WHITE_GATE


def is_fortress_shatra_deploy(from_cell: int, to_cell: int, color: str) -> bool:
    """Шатра выставляется из крепости на большое поле."""
    if not is_main_field_cell(to_cell):
        return False
    if color == "белый":
        return from_cell in WHITE_FORTRESS_CELLS
    return from_cell in BLACK_FORTRESS_CELLS


def is_biy_deploy_to_main_field(from_cell: int, to_cell: int, color: str) -> bool:
    """Бий (или из ворот) выходит на большое поле."""
    if not is_main_field_cell(to_cell):
        return False
    if color == "белый":
        return from_cell == WHITE_GATE or from_cell in WHITE_FORTRESS_CELLS
    return from_cell == BLACK_GATE or from_cell in BLACK_FORTRESS_CELLS


def biy_anchor_cells(color: str) -> frozenset[int]:
    return BLACK_BIY_ANCHOR if color == "черный" else WHITE_BIY_ANCHOR


def batyr_anchor_cells(color: str) -> frozenset[int]:
    return BLACK_BATYR_ANCHOR if color == "черный" else WHITE_BATYR_ANCHOR


def piece_name_at(cells: dict, cell: int) -> str | None:
    """Occupant at cell; accepts int or str board keys."""
    name = cells.get(cell)
    if name is None:
        name = cells.get(str(cell))
    return name


def piece_color_from_name(name: str) -> str:
    return "белый" if "бел" in name else "черный"


def count_color_on_main_field(cells: dict, color: str) -> int:
    """Pieces of one color on the main field (11–52), for opponent-mass checks."""
    total = 0
    for cell in MAIN_FIELD_CELLS:
        name = piece_name_at(cells, cell)
        if name and piece_color_from_name(name) == color:
            total += 1
    return total


def main_field_density(cells: dict) -> int:
    return sum(1 for c in MAIN_FIELD_CELLS if piece_name_at(cells, c))


def biy_anchor_factor(density: int, crowded_threshold: int) -> float:
    if density >= crowded_threshold:
        return 1.0
    return BIY_ANCHOR_SPARSE_FACTOR
