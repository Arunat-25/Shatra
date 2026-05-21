import copy
from game_engine.game_logic import GameLogic
from game_engine.dictionaries import (
    shatra_and_biy_possible_captures,
    batyr_moves_and_captures,
)

PIECE_VALUES = {"шатра": 100, "батыр": 300, "бий": 500}
CENTER = {20, 21, 22, 23, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43}

_logic = GameLogic()  # единственный экземпляр для хинтов


def _count_pieces(cells):
    return sum(1 for v in cells.values() if v is not None)


def evaluate(cells, ai_color):
    score = 0
    for cell, piece_name in cells.items():
        if piece_name is None:
            continue
        color = "белый" if "бел" in piece_name else "черный"
        ptype = piece_name.split()[-1]
        val = PIECE_VALUES.get(ptype, 0)
        if color == ai_color:
            score += val
            if cell in CENTER:
                score += 20
            if ptype == "шатра":
                if (ai_color == "белый" and cell in {1, 2, 3}) or \
                   (ai_color == "черный" and cell in {60, 61, 62}):
                    score += 50
        else:
            score -= val
            if cell in CENTER:
                score -= 20
    return score


def get_legal_moves(cells, color):
    """Все легальные ходы через GameLogic.get_hints.
    Автоматически учитывает обязательные взятия."""
    moves = []
    for cell, name in cells.items():
        if name is None:
            continue
        if ("бел" in name and color != "белый") or ("чер" in name and color != "черный"):
            continue
        result = _logic.get_hints(cells, color, cell)
        for target in (result.essential_positions or []):
            moves.append((cell, target))
    return moves


def _apply_move(cells, from_cell, to_cell):
    """Применить ход: переместить + взять врага."""
    nc = copy.copy(cells)
    nc[to_cell] = nc[from_cell]
    nc[from_cell] = None
    piece_name = nc[to_cell]
    if piece_name is None:
        return nc
    color = "белый" if "бел" in piece_name else "черный"
    ptype = piece_name.split()[-1]

    if ptype in ("шатра", "бий"):
        cap = shatra_and_biy_possible_captures.get(from_cell, {})
        ec = cap.get(to_cell)
        if ec and nc.get(ec) and color not in nc[ec]:
            nc[ec] = None

    elif ptype == "батыр":
        for direction in batyr_moves_and_captures.get(from_cell, []):
            if to_cell in direction:
                for cell in direction:
                    if cell == to_cell:
                        break
                    cp = nc.get(cell)
                    if cp and color not in cp:
                        nc[cell] = None
                        break
                break
    return nc


def minimax(cells, depth, alpha, beta, maximizing, ai_color):
    if depth == 0:
        return evaluate(cells, ai_color), None

    current = ai_color if maximizing else ("белый" if ai_color == "черный" else "черный")
    all_moves = get_legal_moves(cells, current)

    if not all_moves:
        return (-99999 if maximizing else 99999), None

    best_move = None
    if maximizing:
        best_val = -99999
        for fm, to in all_moves:
            nc = _apply_move(cells, fm, to)
            val, _ = minimax(nc, depth - 1, alpha, beta, False, ai_color)
            if val > best_val:
                best_val = val
                best_move = (fm, to)
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return best_val, best_move
    else:
        best_val = 99999
        for fm, to in all_moves:
            nc = _apply_move(cells, fm, to)
            val, _ = minimax(nc, depth - 1, alpha, beta, True, ai_color)
            if val < best_val:
                best_val = val
                best_move = (fm, to)
            beta = min(beta, val)
            if beta <= alpha:
                break
        return best_val, best_move


def get_best_move(cells, ai_color, depth=3):
    if not cells:
        return None
    n = _count_pieces(cells)
    actual_depth = 3 if n < 20 else 2
    if depth is not None:
        actual_depth = min(depth, actual_depth)
    _, best = minimax(cells, actual_depth, -99999, 99999, True, ai_color)
    return best