import copy
from game_engine.game_logic import GameLogic
from game_engine.moves import execute_move
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


def get_legal_moves(cells, color, batyr_captured_this_turn=None):
    """Все легальные ходы через GameLogic.get_hints.
    Автоматически учитывает обязательные взятия."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []
    moves = []
    for cell, name in cells.items():
        if name is None:
            continue
        if ("бел" in name and color != "белый") or ("чер" in name and color != "черный"):
            continue
        result = _logic.get_hints(cells, color, cell, batyr_captured_this_turn=batyr_captured_this_turn)
        for target in (result.essential_positions or []):
            moves.append((cell, target))
    return moves


def minimax(cells, depth, alpha, beta, maximizing, ai_color, batyr_captured_this_turn=None):
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []
    if depth == 0:
        return evaluate(cells, ai_color), None

    current = ai_color if maximizing else ("белый" if ai_color == "черный" else "черный")
    all_moves = get_legal_moves(cells, current, batyr_captured_this_turn)

    if not all_moves:
        return (-99999 if maximizing else 99999), None

    best_move = None
    if maximizing:
        best_val = -99999
        for fm, to in all_moves:
            nc, _, _ = execute_move(cells, fm, to, current, batyr_captured_this_turn)
            val, _ = minimax(nc, depth - 1, alpha, beta, False, ai_color, batyr_captured_this_turn)
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
            nc, _, _ = execute_move(cells, fm, to, current, batyr_captured_this_turn)
            val, _ = minimax(nc, depth - 1, alpha, beta, True, ai_color, batyr_captured_this_turn)
            if val < best_val:
                best_val = val
                best_move = (fm, to)
            beta = min(beta, val)
            if beta <= alpha:
                break
        return best_val, best_move


def get_best_move(cells, ai_color, depth=3, batyr_captured_this_turn=None):
    if not cells:
        return None
    n = _count_pieces(cells)
    actual_depth = 3 if n < 20 else 2
    if depth is not None:
        actual_depth = min(depth, actual_depth)
    _, best = minimax(cells, actual_depth, -99999, 99999, True, ai_color, batyr_captured_this_turn)
    return best