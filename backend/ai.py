"""Улучшенный AI для Shatra с продвинутой оценкой и поиском."""
import math
import time
from game_engine.hints import get_hints
from game_engine.moves import execute_move

PIECE_VALUES = {"шатра": 100, "батыр": 300, "бий": 500}
AI_TIME_LIMITS = ((30, 0.3), (20, 0.5), (12, 0.8))
WHITE_PROMOTION_CELLS = {1, 2, 3}
BLACK_PROMOTION_CELLS = {60, 61, 62}
CRITICAL_BIY_PENALTY = 100000
THREAT_ADJACENT_PENALTY = 80
THREATENED_ENEMY_BONUS = 80
UNDER_ATTACK_PENALTY = 500  # штраф за фигуру под боем
MAX_MOVES_PER_NODE = 12


def _count_pieces(cells):
    return sum(1 for v in cells.values() if v is not None)


SHATRA_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    10, 12, 14, 14, 14, 14, 12, 10,
    15, 18, 20, 20, 20, 20, 18, 15,
    20, 24, 28, 28, 28, 28, 24, 20,
    25, 30, 35, 35, 35, 35, 30, 25,
    30, 36, 42, 42, 42, 42, 36, 30,
    35, 42, 50, 50, 50, 50, 42, 35,
    40, 50, 60, 70, 70, 60, 50, 40,
]

BIY_TABLE = [
    60, 50, 40, 30, 30, 40, 50, 60,
    50, 30, 20, 10, 10, 20, 30, 50,
    40, 20,  0, -10,-10,  0, 20, 40,
    30, 10, -10,-20,-20,-10, 10, 30,
    30, 10, -10,-20,-20,-10, 10, 30,
    40, 20,  0, -10,-10,  0, 20, 40,
    50, 30, 20, 10, 10, 20, 30, 50,
    60, 50, 40, 30, 30, 40, 50, 60,
]

BATYR_TABLE = [
     0,  0,  5, 10, 10,  5,  0,  0,
     5, 10, 15, 20, 20, 15, 10,  5,
    10, 15, 25, 30, 30, 25, 15, 10,
    10, 20, 30, 40, 40, 30, 20, 10,
    10, 20, 30, 40, 40, 30, 20, 10,
    10, 15, 25, 30, 30, 25, 15, 10,
     5, 10, 15, 20, 20, 15, 10,  5,
     0,  0,  5, 10, 10,  5,  0,  0,
]


def _mirror_cell(cell):
    row = cell // 8
    col = cell % 8
    return (7 - row) * 8 + col


def _shatra_promotion_progress(color, cell):
    row = cell // 8
    if color == "белый":
        if row <= 1:
            return 120
        elif row == 2:
            return 50
        elif row == 3:
            return 20
        return 0
    else:
        if row >= 6:
            return 120
        elif row == 5:
            return 50
        elif row == 4:
            return 20
        return 0


def _is_piece_under_attack(cells, cell, by_color):
    """Проверяет: может ли фигура цвета by_color съесть фигуру на cell.
    Использует get_hints для всех вражеских фигур.
    """
    for from_cell, piece in cells.items():
        if piece is None:
            continue
        if ("бел" in piece and by_color != "белый") or ("чер" in piece and by_color != "черный"):
            continue
        
        result = get_hints(cells, by_color, from_cell)
        for target in (result.essential_positions or []):
            if target == cell:
                return True
    
    return False


def evaluate(cells, ai_color):
    """Быстрая оценка с учётом: подставы, бий под угрозой, превращение."""
    score = 0
    opponent_color = "белый" if ai_color == "черный" else "черный"
    our_biy_cell = None
    enemy_biy_cell = None
    under_attack_count = 0

    for cell, piece_name in cells.items():
        if piece_name is None:
            continue

        color = "белый" if "бел" in piece_name else "черный"
        ptype = piece_name.split()[-1]
        val = PIECE_VALUES.get(ptype, 0)
        sign = 1 if color == ai_color else -1

        score += sign * val

        idx = _mirror_cell(cell) if color == "черный" else cell
        if ptype == "шатра":
            score += sign * SHATRA_TABLE[idx]
            score += sign * _shatra_promotion_progress(color, cell)
        elif ptype == "бий":
            score += sign * BIY_TABLE[idx]
            if color == ai_color:
                our_biy_cell = cell
            else:
                enemy_biy_cell = cell
        elif ptype == "батыр":
            score += sign * BATYR_TABLE[idx]
            row = cell // 8
            col = cell % 8
            if 2 <= row <= 5 and 2 <= col <= 5:
                score += sign * 15

    # Штраф за свои фигуры (кроме бия) под ударом
    for cell, piece_name in cells.items():
        if piece_name is None:
            continue
        color = "белый" if "бел" in piece_name else "черный"
        if color != ai_color:
            continue
        ptype = piece_name.split()[-1]
        if ptype == "бий":
            continue
        if _is_piece_under_attack(cells, cell, opponent_color):
            under_attack_count += 1
            score -= UNDER_ATTACK_PENALTY

    # Защита своего бия
    if our_biy_cell is not None:
        if _is_piece_under_attack(cells, our_biy_cell, opponent_color):
            score -= CRITICAL_BIY_PENALTY

    # Охота на вражеского бия
    if enemy_biy_cell is not None:
        threat = 0
        r, c = enemy_biy_cell // 8, enemy_biy_cell % 8
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < 8 and 0 <= nc < 8:
                    adj = nr * 8 + nc
                    p = cells.get(adj)
                    if p and ai_color == ("белый" if "бел" in p else "черный"):
                        threat += 1
        score += threat * THREATENED_ENEMY_BONUS

        if _is_piece_under_attack(cells, enemy_biy_cell, ai_color):
            score += CRITICAL_BIY_PENALTY

    return score


def get_legal_moves(cells, color, batyr_captured_this_turn=None, chain_capture_cell=None):
    """Все легальные ходы через get_hints."""
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []
    moves = []
    for cell, name in cells.items():
        if name is None:
            continue
        if ("бел" in name and color != "белый") or ("чер" in name and color != "черный"):
            continue
        result = get_hints(
            cells, color, cell,
            batyr_captured_this_turn=batyr_captured_this_turn,
            chain_capture_cell=chain_capture_cell,
        )
        for target in (result.essential_positions or []):
            moves.append((cell, target))
    return moves


def _move_priority(cells, move, color):
    """Приоритет хода: взятие бия > взятие батыра > превращение > взятие > остальное."""
    fm, to = move
    piece = cells.get(fm)
    if piece is None:
        return 0

    ptype = piece.split()[-1]
    enemy_prefix = "чер" if color == "белый" else "бел"

    if ptype in ("шатра", "бий"):
        from game_engine.dictionaries import shatra_and_biy_possible_captures
        captures = shatra_and_biy_possible_captures.get(fm, {})
        if to in captures:
            ec = captures[to]
            ep = cells.get(ec)
            if ep and enemy_prefix in ep:
                et = ep.split()[-1]
                if et == "бий":
                    return 10000
                if et == "батыр":
                    return 5000
                return 3000

    if ptype == "батыр":
        target = cells.get(to)
        if target and enemy_prefix in target:
            et = target.split()[-1]
            if et == "бий":
                return 10000
            if et == "батыр":
                return 5000
            return 3000

    if ptype == "шатра":
        if color == "белый" and to in WHITE_PROMOTION_CELLS:
            return 2000
        if color == "черный" and to in BLACK_PROMOTION_CELLS:
            return 2000

    return 0


def quiescence_search(cells, alpha, beta, maximizing, ai_color, batyr_captured_this_turn=None, depth=0, max_qdepth=2, start_time=None, time_limit=math.inf):
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    if start_time is not None and time.time() - start_time > time_limit:
        return evaluate(cells, ai_color)

    if depth >= max_qdepth:
        return evaluate(cells, ai_color)

    stand_pat = evaluate(cells, ai_color)

    if maximizing:
        if stand_pat >= beta:
            return beta
        if alpha < stand_pat:
            alpha = stand_pat
    else:
        if stand_pat <= alpha:
            return alpha
        if beta > stand_pat:
            beta = stand_pat

    current = ai_color if maximizing else ("белый" if ai_color == "черный" else "черный")
    enemy_prefix = "чер" if current == "белый" else "бел"

    capture_moves = []
    for cell, name in cells.items():
        if name is None:
            continue
        if ("бел" in name and current != "белый") or ("чер" in name and current != "черный"):
            continue
        result = get_hints(cells, current, cell, batyr_captured_this_turn=batyr_captured_this_turn)
        for target in (result.essential_positions or []):
            piece_at_target = cells.get(target)
            if piece_at_target and enemy_prefix in piece_at_target:
                capture_moves.append((cell, target))

    if not capture_moves:
        return stand_pat

    for fm, to in capture_moves:
        nc, _, new_batyr = execute_move(cells, fm, to, current, batyr_captured_this_turn)
        if maximizing:
            val = quiescence_search(nc, alpha, beta, False, ai_color, new_batyr, depth + 1, max_qdepth, start_time, time_limit)
            if val >= beta:
                return beta
            if val > alpha:
                alpha = val
        else:
            val = quiescence_search(nc, alpha, beta, True, ai_color, new_batyr, depth + 1, max_qdepth, start_time, time_limit)
            if val <= alpha:
                return alpha
            if val < beta:
                beta = val

    return alpha if maximizing else beta


def minimax(cells, depth, alpha, beta, maximizing, ai_color, batyr_captured_this_turn=None, start_time=None, time_limit=math.inf):
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    if start_time is not None and time.time() - start_time > time_limit:
        return evaluate(cells, ai_color), None

    if depth == 0:
        val = quiescence_search(cells, alpha, beta, maximizing, ai_color, batyr_captured_this_turn, start_time=start_time, time_limit=time_limit)
        return val, None

    current = ai_color if maximizing else ("белый" if ai_color == "черный" else "черный")
    all_moves = get_legal_moves(cells, current, batyr_captured_this_turn)

    if not all_moves:
        return (-math.inf if maximizing else math.inf), None

    if len(all_moves) > MAX_MOVES_PER_NODE:
        all_moves.sort(key=lambda m: _move_priority(cells, m, current), reverse=True)
        all_moves = all_moves[:MAX_MOVES_PER_NODE]

    best_move = None
    if maximizing:
        best_val = -math.inf
        for fm, to in all_moves:
            nc, _, new_batyr = execute_move(cells, fm, to, current, batyr_captured_this_turn)
            val, _ = minimax(nc, depth - 1, alpha, beta, False, ai_color, new_batyr, start_time, time_limit)
            if val > best_val:
                best_val = val
                best_move = (fm, to)
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return best_val, best_move

    best_val = math.inf
    for fm, to in all_moves:
        nc, _, new_batyr = execute_move(cells, fm, to, current, batyr_captured_this_turn)
        val, _ = minimax(nc, depth - 1, alpha, beta, True, ai_color, new_batyr, start_time, time_limit)
        if val < best_val:
            best_val = val
            best_move = (fm, to)
        beta = min(beta, val)
        if beta <= alpha:
            break
    return best_val, best_move


def _get_time_limit(cells):
    n = _count_pieces(cells)
    for threshold, limit in AI_TIME_LIMITS:
        if n > threshold:
            return limit
    return 2.0


def get_best_move(cells, ai_color, depth=3, batyr_captured_this_turn=None, chain_capture_cell=None):
    if not cells:
        return None

    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    # Мгновенное взятие бия
    biy_capture_move = _find_biy_capture_move(cells, ai_color)
    if biy_capture_move:
        return biy_capture_move

    n = _count_pieces(cells)
    time_limit = _get_time_limit(cells)

    if n > 20:
        time_limit = min(time_limit, 0.3)
        max_depth = min(depth, 2)
    elif n > 12:
        time_limit = min(time_limit, 0.5)
        max_depth = min(depth, 3)
    else:
        time_limit = min(time_limit, 0.8)
        max_depth = min(depth, 4)

    # Цепочка обязательных взятий
    if chain_capture_cell:
        result = get_hints(cells, ai_color, chain_capture_cell, batyr_captured_this_turn=batyr_captured_this_turn, chain_capture_cell=chain_capture_cell)
        chain_moves = [(chain_capture_cell, t) for t in (result.essential_positions or [])]
        # Проверяем: оставляем только ходы-взятия
        capture_chain_moves = []
        for fm, to in chain_moves:
            nc, captured, new_batyr = execute_move(cells, fm, to, ai_color, batyr_captured_this_turn)
            if captured:  # ход является взятием
                capture_chain_moves.append((fm, to))
        if capture_chain_moves:
            capture_chain_moves.sort(key=lambda m: _move_priority(cells, m, ai_color), reverse=True)
            return capture_chain_moves[0]

    best_move = None
    start_time = time.time()

    for d in range(1, max_depth + 1):
        elapsed = time.time() - start_time
        if elapsed > time_limit * 0.6:
            break

        try:
            _, move = minimax(cells, d, -math.inf, math.inf, True, ai_color, batyr_captured_this_turn, start_time, time_limit)
            if move is not None:
                best_move = move
        except RecursionError:
            break

    # Fallback
    if best_move is None:
        all_moves = get_legal_moves(cells, ai_color, batyr_captured_this_turn, chain_capture_cell)
        if all_moves:
            all_moves.sort(key=lambda m: _move_priority(cells, m, ai_color), reverse=True)
            best_move = all_moves[0]

    return best_move


def _find_biy_capture_move(cells, ai_color):
    """Ищет взятие бия через get_hints."""
    for from_cell, piece in cells.items():
        if not piece or not piece.startswith(ai_color):
            continue
        result = get_hints(cells, ai_color, from_cell)
        for to_cell in (result.essential_positions or []):
            target = cells.get(to_cell)
            if target and "бий" in target:
                enemy_prefix = "черный" if ai_color == "белый" else "белый"
                if target.startswith(enemy_prefix):
                    return (from_cell, to_cell)
    return None
