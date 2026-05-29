"""AI для Шатры: v2.5-hotfix — Сильная тактика + стабильность."""
from __future__ import annotations

import copy
import math
import time
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

from game_engine.board import Board
from game_engine.dictionaries import shatra_and_biy_possible_captures
from game_engine.endgame import is_game_over
from game_engine.hints import get_hints
from game_engine.moves import process_move
from game_engine.validation import find_captured_enemy, get_all_mandatory_captures

Move = Tuple[int, int]

def _dbg(*_args, **_kwargs):
    """No-op. Оставлен, чтобы не трогать места вызова; отладочный лог удалён."""
    return None

# ═══════════════════════════════════════════════════════════
# 🎯 КОНСТАНТЫ (СБАЛАНСИРОВАННЫЕ)
# ═══════════════════════════════════════════════════════════
PIECE_VALUES = {"шатра": 100, "батыр": 350, "бий": 10_000}
WIN_SCORE = 1_000_000
LOSE_SCORE = -1_000_000
BIY_LOSS_PENALTY = 800_000  # ❗ Не 999к: позволяем поиску находить защиту
HANGING_PENALTY = 350
PROMOTION_BONUS = 2_500     # ❗ Не 18к: тактика важнее немедленного превращения
PROMOTION_PROGRESS_WEIGHT = 12
POSITION_SCALE = 3.0

FORCED_TRAP_BONUS = 15_000
CHAIN_CAPTURE_BONUS = 8_000
SACRIFICE_SETUP_BONUS = 5_000

WHITE_PROMOTION = {1, 2, 3}
BLACK_PROMOTION = {60, 61, 62}

AI_TIME_LIMITS = ((30, 0.35), (20, 0.55), (12, 0.9))
MAX_MOVES_PER_NODE = 14
MAX_QUIESCE_DEPTH = 4

# ═══════════════════════════════════════════════════════════
# ♟️ ТАБЛИЦЫ (без изменений)
# ═══════════════════════════════════════════════════════════
SHATRA_TABLE = [0,0,0,0,0,0,0,0, 30,36,42,42,42,42,36,30, 45,54,60,60,60,60,54,45, 60,72,84,84,84,84,72,60, 75,90,105,105,105,105,90,75, 90,108,126,126,126,126,108,90, 105,126,150,150,150,150,126,105, 120,150,180,210,210,180,150,120]
BIY_TABLE = [180,150,120,90,90,120,150,180, 150,90,60,30,30,60,90,150, 120,60,0,-30,-30,0,60,120, 90,30,-30,-60,-60,-30,30,90, 90,30,-30,-60,-60,-30,30,90, 120,60,0,-30,-30,0,60,120, 150,90,60,30,30,60,90,150, 180,150,120,90,90,120,150,180]
BATYR_TABLE = [0,0,15,30,30,15,0,0, 15,30,45,60,60,45,30,15, 30,45,75,90,90,75,45,30, 30,60,90,120,120,90,60,30, 30,60,90,120,120,90,60,30, 30,45,75,90,90,75,45,30, 15,30,45,60,60,45,30,15, 0,0,15,30,30,15,0,0]

@dataclass
class SearchState:
    cells: dict
    to_move: str
    chain_cell: Optional[int] = None
    batyr_captured: List[int] = None
    def __post_init__(self):
        if self.batyr_captured is None:
            self.batyr_captured = []

# ═══════════════════════════════════════════════════════════
# 🛠 БЕЗОПАСНЫЕ УТИЛИТЫ (✅ ФИКС AttributeError)
# ═══════════════════════════════════════════════════════════
def _safe_piece_type(name: Optional[str]) -> str:
    """✅ FIX: безопасное извлечение типа фигуры"""
    if not name:
        return ""
    return name.split()[-1]

def _opponent(color: str) -> str: return "черный" if color == "белый" else "белый"
def _piece_color(name: str) -> str: return "белый" if "бел" in name else "черный"
def _count_pieces(cells: dict) -> int: return sum(1 for v in cells.values() if v is not None)
def _mirror_cell(cell: int) -> int: return (7 - cell // 8) * 8 + (cell % 8)
def _distance(c1: int, c2: int) -> int: return abs(c1//8 - c2//8) + abs(c1%8 - c2%8)

def _find_biy_cell(cells: dict, color: str) -> Optional[int]:
    for c, n in cells.items():
        if n and "бий" in n and _piece_color(n) == color:
            return c
    return None

def _clear_promotion_path(cells: dict, color: str, cell: int) -> bool:
    row, col = cell // 8, cell % 8
    target_rows = range(row - 1, -1, -1) if color == "белый" else range(row + 1, 8)
    for r in target_rows:
        if cells.get(r * 8 + col) is not None:
            return False
    return True

def _is_cell_capturable(cells: dict, by_color: str, target_cell: int) -> bool:
    if cells.get(target_cell) is None:
        return False
    board = Board(cells)
    for fm, to in get_all_mandatory_captures(board, by_color, []):
        p = board.get_piece_object(fm)
        if p and find_captured_enemy(cells, p, fm, to, []) == target_cell:
            return True
    for fm, name in cells.items():
        if not name or _piece_color(name) != by_color:
            continue
        p = board.get_piece_object(fm)
        if not p:
            continue
        pt = _safe_piece_type(name)
        if pt in ("шатра", "бий"):
            for to, ec in shatra_and_biy_possible_captures.get(fm, {}).items():
                if ec == target_cell and p.can_capture(cells, fm, to, []):
                    return True
        elif pt == "батыр":
            for to in (get_hints(cells, by_color, fm).essential_positions or []):
                if p.can_capture(cells, fm, to, []) and find_captured_enemy(cells, p, fm, to, []) == target_cell:
                    return True
    return False

def _get_all_captures_for_color(cells: dict, color: str) -> List[Tuple[int, int, Optional[int]]]:
    captures = []
    board = Board(cells)
    for fm, to in get_all_mandatory_captures(board, color, []):
        p = board.get_piece_object(fm)
        if p:
            captures.append((fm, to, find_captured_enemy(cells, p, fm, to, [])))
    for fm, name in cells.items():
        if not name or _piece_color(name) != color:
            continue
        p = board.get_piece_object(fm)
        if not p or _safe_piece_type(name) not in ("шатра", "бий"):
            continue
        for to, ec in shatra_and_biy_possible_captures.get(fm, {}).items():
            victim = cells.get(ec)
            if victim and _piece_color(victim) != color and not cells.get(to):
                if p.can_capture(cells, fm, to, []):
                    if (fm, to, ec) not in captures:
                        captures.append((fm, to, ec))
    return captures

def _simulate_capture_sequence(cells: dict, color: str, start_move: Move, max_depth: int = 4) -> Tuple[int, List[Move]]:
    fm, to = start_move
    board = Board(cells)
    piece = board.get_piece_object(fm)
    if not piece:
        return 0, []
    captured = find_captured_enemy(cells, piece, fm, to, [])
    if captured is None or not cells.get(captured):  # ✅ FIX: проверка на None
        return 0, []
    
    result = process_move(copy.deepcopy(cells), color, fm, to,
                          chain_capture_cell=captured, batyr_captured_this_turn=[], position_history={})
    if not result.updated_positions:
        return 0, []
    
    new_cells = result.updated_positions
    chain = [start_move]
    victim_name = cells.get(captured)
    total_value = PIECE_VALUES.get(_safe_piece_type(victim_name), 0) if victim_name else 0  # ✅ FIX
    next_chain = result.position_for_mandatory_capture
    
    for _ in range(max_depth - 1):
        if not next_chain:
            break
        found = False
        for fm_c, name in new_cells.items():
            if not name or _piece_color(name) != color:
                continue
            p = Board(new_cells).get_piece_object(fm_c)
            if not p:
                continue
            for to_c, ec in shatra_and_biy_possible_captures.get(fm_c, {}).items():
                if ec == next_chain and not new_cells.get(to_c) and p.can_capture(new_cells, fm_c, to_c, []):
                    v_name = new_cells.get(ec)
                    if v_name:  # ✅ FIX
                        total_value += PIECE_VALUES.get(_safe_piece_type(v_name), 0)
                    chain.append((fm_c, to_c))
                    res = process_move(copy.deepcopy(new_cells), color, fm_c, to_c,
                                       chain_capture_cell=ec, batyr_captured_this_turn=[], position_history={})
                    if res.updated_positions:
                        new_cells = res.updated_positions
                        next_chain = res.position_for_mandatory_capture
                    found = True
                    break
            if found:
                break
        if not found:
            break
    return total_value, chain

def _evaluate_forced_trap(cells: dict, ai_color: str, test_move: Move) -> int:
    fm, to = test_move
    result = process_move(copy.deepcopy(cells), _opponent(ai_color), fm, to,
                          chain_capture_cell=None, batyr_captured_this_turn=[], position_history={})
    if not result.updated_positions:
        return 0
    new_cells = result.updated_positions
    opp = _opponent(ai_color)
    opp_mandatory = get_all_mandatory_captures(Board(new_cells), opp, [])
    if not opp_mandatory:
        return 0
    all_opp = get_legal_moves(SearchState(new_cells, opp))
    if len(opp_mandatory) == len(all_opp) and len(opp_mandatory) > 0:
        best_for_us = -math.inf
        for opp_fm, opp_to in opp_mandatory:
            opp_res = process_move(copy.deepcopy(new_cells), opp, opp_fm, opp_to,
                                   chain_capture_cell=None, batyr_captured_this_turn=[], position_history={})
            if not opp_res.updated_positions:
                continue
            after_opp = opp_res.updated_positions
            our_caps = _get_all_captures_for_color(after_opp, ai_color)
            chain_value, biy_threat = 0, 0
            for c_fm, c_to, c_captured in our_caps:
                if c_captured and "бий" in (after_opp.get(c_captured) or ""):
                    biy_threat = BIY_LOSS_PENALTY // 2
                elif c_captured:
                    v_name = after_opp.get(c_captured)
                    chain_value += PIECE_VALUES.get(_safe_piece_type(v_name), 0) if v_name else 0  # ✅ FIX
            if our_caps:
                best_cap = max(our_caps, key=lambda x: PIECE_VALUES.get(_safe_piece_type(after_opp.get(x[2])), 0) if x[2] else 0)
                sim_val, _ = _simulate_capture_sequence(after_opp, ai_color, (best_cap[0], best_cap[1]))
                chain_value = max(chain_value, sim_val)
            best_for_us = max(best_for_us, chain_value + biy_threat)
        if best_for_us > 0:
            return FORCED_TRAP_BONUS + min(best_for_us, 10_000)
    for opp_fm, opp_to in opp_mandatory:
        opp_p = Board(new_cells).get_piece_object(opp_fm)
        if opp_p:
            opp_cap = find_captured_enemy(new_cells, opp_p, opp_fm, opp_to, [])
            if opp_cap and "бий" in (new_cells.get(opp_cap) or ""):
                return FORCED_TRAP_BONUS // 2
    return 0

def _evaluate_chain_potential(cells: dict, ai_color: str, move: Move) -> int:
    fm, to = move
    board = Board(cells)
    piece = board.get_piece_object(fm)
    if not piece:
        return 0
    captured = find_captured_enemy(cells, piece, fm, to, [])
    if captured:
        value, chain = _simulate_capture_sequence(cells, ai_color, move, max_depth=4)
        if len(chain) >= 2:
            return CHAIN_CAPTURE_BONUS + min(value, 5_000)
        return value // 2
    result = process_move(copy.deepcopy(cells), ai_color, fm, to,
                          chain_capture_cell=None, batyr_captured_this_turn=[], position_history={})
    if not result.updated_positions:
        return 0
    new_caps = _get_all_captures_for_color(result.updated_positions, ai_color)
    old_caps = _get_all_captures_for_color(cells, ai_color)
    if len(new_caps) > len(old_caps):
        best_new = max(
            ((PIECE_VALUES.get(_safe_piece_type(result.updated_positions.get(c[2])), 0) if c[2] else 0)
            for c in new_caps if c not in old_caps),
            default=0
        )
        return SACRIFICE_SETUP_BONUS // 2 + best_new // 2
    return 0

def _evaluate_biy_threats(cells: dict, ai_color: str) -> int:
    score = 0
    opp = _opponent(ai_color)
    for cell, name in cells.items():
        if not name or _safe_piece_type(name) not in ("шатра", "батыр"):
            continue
        pc = _piece_color(name)
        sign = 1 if pc == ai_color else -1
        tgt = opp if pc == ai_color else ai_color
        biy = _find_biy_cell(cells, tgt)
        if biy is None:
            continue
        d = _distance(cell, biy)
        if d <= 2:
            score += (150 if pc == ai_color else -200) * (3 - d)
    return score

def _apply_process_move(state: SearchState, fm: int, to: int):
    return process_move(copy.deepcopy(state.cells), state.to_move, fm, to,
                        chain_capture_cell=state.chain_cell,
                        batyr_captured_this_turn=list(state.batyr_captured),
                        position_history={})

def _child_state(state: SearchState, fm: int, to: int):
    result = _apply_process_move(state, fm, to)
    if not result.updated_positions:
        return None, result
    nc = result.position_for_mandatory_capture
    nm = result.movers_color or state.to_move
    if nc and nm == state.to_move:
        return SearchState(result.updated_positions, state.to_move, nc, list(result.captured_pieces or [])), result
    return SearchState(result.updated_positions, nm, None, []), result

def _we_won(r, c): return r.game_over and r.winner_color == c
def _we_lost(r, c): return r.game_over and bool(r.winner_color) and r.winner_color != c

def _move_exposes_biy(state, move, ai_color):
    child, res = _child_state(state, move[0], move[1])
    if child is None:
        return True
    if res.game_over:
        return _we_lost(res, ai_color)
    our = _find_biy_cell(child.cells, ai_color)
    if not our:
        return False
    opp = _opponent(ai_color)
    if _is_cell_capturable(child.cells, opp, our):
        return True
    if child.to_move == opp:
        for f, t in get_all_mandatory_captures(Board(child.cells), opp, []):
            p = Board(child.cells).get_piece_object(f)
            if p and find_captured_enemy(child.cells, p, f, t, []) == our:
                return True
    return False

def _shatra_promotion_progress(color: str, cell: int) -> int:
    row = cell // 8
    if color == "белый":
        return 120 if row <= 1 else 55 if row == 2 else 25 if row == 3 else 0
    return 120 if row >= 6 else 55 if row == 5 else 25 if row == 4 else 0

def _terminal_score(result, ai_color: str) -> Optional[int]:
    if not result.game_over:
        return None
    if _we_won(result, ai_color):
        return WIN_SCORE
    if _we_lost(result, ai_color):
        return LOSE_SCORE
    return 0

# ═══════════════════════════════════════════════════════════
# 📊 ОЦЕНКА (СОХРАНЕНА ТАКТИКА + ✅ ФИКСЫ)
# ═══════════════════════════════════════════════════════════
def evaluate(cells, ai_color, test_move=None):
    over, winner_color, _draw = is_game_over(Board(cells))
    if over and winner_color:
        if winner_color == ai_color:
            return WIN_SCORE
        return LOSE_SCORE

    score = 0
    opp = _opponent(ai_color)
    our_biy = _find_biy_cell(cells, ai_color)
    enemy_biy = _find_biy_cell(cells, opp)

    for cell, name in cells.items():
        if not name:
            continue
        color = _piece_color(name)
        pt = _safe_piece_type(name)
        sign = 1 if color == ai_color else -1
        score += sign * PIECE_VALUES.get(pt, 0)
        idx = _mirror_cell(cell) if color == "черный" else cell

        if pt == "шатра":
            score += sign * SHATRA_TABLE[idx] * POSITION_SCALE
            score += sign * _shatra_promotion_progress(color, cell) * PROMOTION_PROGRESS_WEIGHT
            if _clear_promotion_path(cells, color, cell):
                score += sign * 50
            promo = WHITE_PROMOTION if color == "белый" else BLACK_PROMOTION
            if cell in promo:
                score += sign * PROMOTION_BONUS
        elif pt == "бий":
            score += sign * BIY_TABLE[idx] * POSITION_SCALE
        elif pt == "батыр":
            score += sign * BATYR_TABLE[idx] * POSITION_SCALE

    if our_biy and _is_cell_capturable(cells, opp, our_biy):
        score -= BIY_LOSS_PENALTY
    if enemy_biy and _is_cell_capturable(cells, ai_color, enemy_biy):
        score += BIY_LOSS_PENALTY // 2

    for cell, name in cells.items():
        if not name or _piece_color(name) != ai_color:
            continue
        pt = _safe_piece_type(name)
        if pt == "бий":
            continue
        if _is_cell_capturable(cells, opp, cell):
            score -= HANGING_PENALTY + PIECE_VALUES.get(pt, 0) // 2

    score += _evaluate_biy_threats(cells, ai_color)

    if test_move:
        score += _evaluate_forced_trap(cells, ai_color, test_move)
        score += _evaluate_chain_potential(cells, ai_color, test_move)

    # ❗ FIX 3: Предупреждающий штраф, если Бий в радиусе атаки, но ещё не под прямым боем
    if our_biy is not None and not _is_cell_capturable(cells, opp, our_biy):
        board = Board(cells)
        for c, name in cells.items():
            if name and _piece_color(name) == opp and _safe_piece_type(name) in ("шатра", "батыр"):
                if _distance(c, our_biy) <= 2:
                    piece = board.get_piece_object(c)
                    if piece:
                        is_threat = False
                        if _safe_piece_type(name) in ("шатра", "бий"):
                            if our_biy in shatra_and_biy_possible_captures.get(c, {}).values():
                                is_threat = True
                        elif _safe_piece_type(name) == "батыр":
                            hints = get_hints(cells, opp, c)
                            if our_biy in (hints.essential_positions or []):
                                is_threat = True
                        if is_threat:
                            score -= BIY_LOSS_PENALTY // 3  # ~266_000: сильно отталкивает, но не ломает поиск

    return score

# ═══════════════════════════════════════════════════════════
# 🔄 ГЕНЕРАЦИЯ И СОРТИРОВКА (СОХРАНЕНА ТАКТИЧЕСКАЯ СОРТИРОВКА)
# ═══════════════════════════════════════════════════════════
def get_legal_moves(state: SearchState) -> List[Move]:
    moves = []
    for c, n in state.cells.items():
        if not n or _piece_color(n) != state.to_move:
            continue
        hints = get_hints(state.cells, state.to_move, c,
                          batyr_captured_this_turn=state.batyr_captured,
                          chain_capture_cell=state.chain_cell)
        for t in (hints.essential_positions or []):
            moves.append((c, t))
    return moves

def _is_capture_move(cells, color, fm, to):
    p = Board(cells).get_piece_object(fm)
    if not p:
        return False
    if _safe_piece_type(cells.get(fm)) in ("шатра", "бий"):
        return to in shatra_and_biy_possible_captures.get(fm, {})
    return bool(p.can_capture(cells, fm, to, []))

def _captured_enemy_type(cells, color, fm, to):
    p = Board(cells).get_piece_object(fm)
    if not p:
        return None
    ec = find_captured_enemy(cells, p, fm, to, [])
    if ec is None:
        return None
    victim = cells.get(ec)
    if not victim or _piece_color(victim) == color:
        return None
    return _safe_piece_type(victim)

def _creates_mandatory_capture_for_opp(cells, ai_color, move):
    fm, to = move
    result = process_move(copy.deepcopy(cells), ai_color, fm, to,
                          chain_capture_cell=None, batyr_captured_this_turn=[], position_history={})
    if not result.updated_positions:
        return False
    opp = _opponent(ai_color)
    # ✅ ИСПРАВЛЕНО: проверяем только обязательные взятия шатрой/батыром
    return len(_get_strict_mandatory_captures(result.updated_positions, opp)) > 0

def _move_sort_key(state, move, ai_color):
    fm, to = move
    cells = state.cells
    piece = cells.get(fm)
    if not piece:
        return -10_000
    ptype = _safe_piece_type(piece)
    score = 0

    child, result = _child_state(state, fm, to)
    if child is None:
        return -10_000

    terminal = _terminal_score(result, ai_color)
    if terminal is not None:
        return terminal

    if _move_exposes_biy(state, move, ai_color):
        return -300_000

    captured = _captured_enemy_type(cells, state.to_move, fm, to)
    if captured == "бий" and state.to_move == ai_color:
        score += 200_000
    elif captured == "батыр":
        score += 8_000
    elif captured == "шатра":
        score += 2_500
    elif _is_capture_move(cells, state.to_move, fm, to):
        score += 1_200

    if ptype == "шатра" and state.to_move == ai_color:
        promo = WHITE_PROMOTION if ai_color == "белый" else BLACK_PROMOTION
        if to in promo:
            score += PROMOTION_BONUS * 2
        score += _shatra_promotion_progress(ai_color, to) * 2

    # ❗ КРИТИЧЕСКИЙ ФИКС: Если Бий делает ход и оказывается под боем — жёстко запрещаем
    # Раньше было score -= 50_000, но это перекрывалось бонусами за взятие (+1_200 / +2_500)
    # Теперь возвращаем -950_000 сразу — это гарантированно ниже любого тактического бонуса
    if ptype == "бий" and state.to_move == ai_color:
        if _is_cell_capturable(child.cells, _opponent(ai_color), to):
            return -950_000

    # ❗ ТАКТИЧЕСКИЕ БОНУСЫ
    if state.to_move == ai_color:
        if _creates_mandatory_capture_for_opp(cells, ai_color, move):
            score += 3_000
        score += _evaluate_chain_potential(cells, ai_color, move) // 2

    return score

def _filter_moves_for_ai(state, moves, ai_color):
    if state.to_move != ai_color:
        return moves
    safe = []
    for move in moves:
        child, result = _child_state(state, move[0], move[1])
        if child is None:
            continue
        if result.game_over and _we_won(result, ai_color):
            safe.append(move)
            continue
        if _move_exposes_biy(state, move, ai_color):
            continue
        safe.append(move)
    if safe:
        return safe
    ranked = sorted(moves, key=lambda m: _move_sort_key(state, m, ai_color), reverse=True)
    return ranked[: max(3, len(ranked) // 3)]

def _ordered_moves(state, ai_color, maximizing):
    moves = get_legal_moves(state)
    if not moves:
        return moves
    if maximizing:
        moves = _filter_moves_for_ai(state, moves, ai_color)
    moves.sort(key=lambda m: _move_sort_key(state, m, ai_color if maximizing else _opponent(ai_color)), reverse=True)
    return moves[:MAX_MOVES_PER_NODE]

def _is_quiescence_move(state, move, ai_color):
    fm, to = move
    cells = state.cells
    if _is_capture_move(cells, state.to_move, fm, to):
        return True
    enemy_biy = _find_biy_cell(cells, _opponent(state.to_move))
    if enemy_biy is not None:
        if state.to_move == _piece_color(cells.get(fm) or ""):
            possible_caps = shatra_and_biy_possible_captures.get(to, {})
            if enemy_biy in possible_caps.values():
                return True
    promo = WHITE_PROMOTION if state.to_move == "белый" else BLACK_PROMOTION
    if to in promo:
        return True
    if _creates_mandatory_capture_for_opp(cells, ai_color, move):
        return True
    return False

def quiescence(state, alpha, beta, maximizing, ai_color, depth=0, start_time=None, time_limit=math.inf):
    if start_time and time.time() - start_time > time_limit:
        return evaluate(state.cells, ai_color)
    stand = evaluate(state.cells, ai_color)
    if depth >= MAX_QUIESCE_DEPTH:
        return stand
    if maximizing:
        if stand >= beta:
            return beta
        alpha = max(alpha, stand)
    else:
        if stand <= alpha:
            return alpha
        beta = min(beta, stand)

    tactical = [m for m in get_legal_moves(state) if _is_quiescence_move(state, m, ai_color)]
    if not tactical:
        return stand

    for move in tactical[:10]:
        child, result = _child_state(state, move[0], move[1])
        if child is None:
            continue

        # ❗ FIX 2: Если сейчас ходит Бий — принудительно углубляемся, чтобы увидеть ответный удар
        moving_piece = state.cells.get(move[0])
        is_biy_move = moving_piece and "бий" in moving_piece
        extra_depth = 1 if is_biy_move else 0

        terminal = _terminal_score(result, ai_color)
        if terminal is not None:
            val = terminal
        else:
            next_max = child.to_move == ai_color
            next_depth = min(depth + 1 + extra_depth, MAX_QUIESCE_DEPTH + 2)  # ограничиваем потолок
            val = quiescence(child, alpha, beta, next_max, ai_color, next_depth, start_time, time_limit)

        if maximizing:
            if val >= beta:
                return beta
            alpha = max(alpha, val)
        else:
            if val <= alpha:
                return alpha
            beta = min(beta, val)
    return alpha if maximizing else beta

def minimax(state, depth, alpha, beta, maximizing, ai_color, start_time=None, time_limit=math.inf):
    if start_time and time.time() - start_time > time_limit:
        return evaluate(state.cells, ai_color), None
    over, winner_color, _draw = is_game_over(Board(state.cells))
    if over and winner_color:
        return evaluate(state.cells, ai_color), None
    if depth == 0:
        val = quiescence(state, alpha, beta, maximizing, ai_color, start_time=start_time, time_limit=time_limit)
        return val, None

    # ❗ АДАПТИВНАЯ ГЛУБИНА для тактики
    current_depth = depth
    if not maximizing and state.to_move == ai_color:
        moves = get_legal_moves(state)
        has_chain = any(_evaluate_chain_potential(state.cells, ai_color, m) > 0 for m in moves[:5])
        if has_chain:
            current_depth = min(depth + 1, 5)

    moves = _ordered_moves(state, ai_color, maximizing)
    if not moves:
        return (LOSE_SCORE if maximizing else WIN_SCORE), None

    best_move, best_val = (None, -math.inf) if maximizing else (None, math.inf)

    if maximizing:
        for move in moves:
            child, result = _child_state(state, move[0], move[1])
            if child is None:
                continue
            terminal = _terminal_score(result, ai_color)
            val = terminal if terminal is not None else minimax(child, current_depth - 1, alpha, beta, child.to_move == ai_color, ai_color, start_time, time_limit)[0]
            if val > best_val:
                best_val, best_move = val, move
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        return best_val, best_move
    else:
        for move in moves:
            child, result = _child_state(state, move[0], move[1])
            if child is None:
                continue
            terminal = _terminal_score(result, ai_color)
            val = terminal if terminal is not None else minimax(child, current_depth - 1, alpha, beta, child.to_move == ai_color, ai_color, start_time, time_limit)[0]
            if val < best_val:
                best_val, best_move = val, move
            beta = min(beta, val)
            if beta <= alpha:
                break
        return best_val, best_move

def _get_time_limit(cells: dict) -> float:
    n = _count_pieces(cells)
    for thr, lim in AI_TIME_LIMITS:
        if n > thr:
            return lim
    return 1.2

def _pick_chain_move(state, ai_color):
    hints = get_hints(state.cells, ai_color, state.chain_cell,
                      batyr_captured_this_turn=state.batyr_captured,
                      chain_capture_cell=state.chain_cell)
    moves = [(state.chain_cell, t) for t in (hints.essential_positions or [])]
    if not moves:
        return None
    safe = _filter_moves_for_ai(state, moves, ai_color)
    safe.sort(key=lambda m: _move_sort_key(state, m, ai_color), reverse=True)
    return safe[0]

def _pick_winning_biy_capture(state, ai_color):
    for move in get_legal_moves(state):
        victim = _captured_enemy_type(state.cells, ai_color, move[0], move[1])
        if victim != "бий":
            continue
        _, result = _child_state(state, move[0], move[1])
        if result.game_over and _we_won(result, ai_color):
            return move
    return None

def _has_obvious_win(cells, ai_color):
    board = Board(cells)
    for move in get_all_mandatory_captures(board, ai_color, []):
        p = board.get_piece_object(move[0])
        if not p:
            continue
        ec = find_captured_enemy(cells, p, move[0], move[1], [])
        if ec is not None:
            victim = cells.get(ec)
            if victim and "бий" in victim:
                return move
    return None

def get_best_move(cells: dict, ai_color: str, depth: int = 3,
                  batyr_captured_this_turn=None, chain_capture_cell=None) -> Optional[Move]:
    if not cells:
        return None
    state = SearchState(cells=cells, to_move=ai_color, chain_cell=chain_capture_cell,
                        batyr_captured=list(batyr_captured_this_turn or []))
    if chain_capture_cell:
        _dbg("H7", "backend/ai.py:get_best_move", "return chain move", {"ai_color": ai_color, "chain": chain_capture_cell})
        return _pick_chain_move(state, ai_color)
    win = _has_obvious_win(cells, ai_color)
    if win:
        _dbg("H7", "backend/ai.py:get_best_move", "return obvious win", {"ai_color": ai_color, "move": win})
        return win
    win_biy = _pick_winning_biy_capture(state, ai_color)
    if win_biy:
        _dbg("H7", "backend/ai.py:get_best_move", "return winning biy capture", {"ai_color": ai_color, "move": win_biy})
        return win_biy

    n = _count_pieces(cells)
    time_limit = _get_time_limit(cells)
    
    # ❗ Больше времени на тактику
    has_tactical = any(_evaluate_chain_potential(cells, ai_color, m) > 0 or 
                       _creates_mandatory_capture_for_opp(cells, ai_color, m)
                       for m in get_legal_moves(state)[:10])
    if has_tactical:
        time_limit = min(time_limit * 1.5, 2.0)
    
    if n > 20:
        time_limit = min(time_limit, 0.35)
        max_depth = min(depth, 2)
    elif n > 12:
        time_limit = min(time_limit, 0.55)
        max_depth = min(depth, 3)
    else:
        time_limit = min(time_limit, 0.95)
        max_depth = min(depth, 4)

    start = time.time()
    best_move = None

    for d in range(1, max_depth + 1):
        if time.time() - start > time_limit * 0.85:
            break
        try:
            _, move = minimax(state, d, -math.inf, math.inf, True, ai_color, start_time=start, time_limit=time_limit)
            if move is not None:
                best_move = move
        except RecursionError:
            break

    if best_move is None:
        moves = _filter_moves_for_ai(state, get_legal_moves(state), ai_color)
        if moves:
            moves.sort(key=lambda m: _move_sort_key(state, m, ai_color), reverse=True)
            top_val = _move_sort_key(state, moves[0], ai_color)
            top_moves = [m for m in moves if _move_sort_key(state, m, ai_color) >= top_val - 50]
            best_move = random.choice(top_moves) if len(top_moves) > 1 else moves[0]

    # Диагностика выбора на конце (помогает понять, почему не выбирается превращение)
    try:
        moves_all = _filter_moves_for_ai(state, get_legal_moves(state), ai_color)
        scored = [(m, _move_sort_key(state, m, ai_color)) for m in moves_all]
        scored.sort(key=lambda x: x[1], reverse=True)
        promo_moves = []
        for fm, to in moves_all:
            piece = cells.get(fm) or ""
            if "шатра" in piece:
                if (ai_color == "черный" and to in BLACK_PROMOTION) or (ai_color == "белый" and to in WHITE_PROMOTION):
                    promo_moves.append((fm, to))
        _dbg("H7", "backend/ai.py:get_best_move", "final choice", {
            "ai_color": ai_color,
            "depth": depth,
            "nPieces": n,
            "best": best_move,
            "top5": [{"move": m, "key": k} for (m, k) in scored[:5]],
            "promoMoves": promo_moves,
            "ourBiy": _find_biy_cell(cells, ai_color),
            "ourBiyCapturableNow": (
                _is_cell_capturable(cells, _opponent(ai_color), _find_biy_cell(cells, ai_color))
                if _find_biy_cell(cells, ai_color) else None
            ),
            "bestExposesBiy": (_move_exposes_biy(state, best_move, ai_color) if best_move else None),
        })
    except Exception:
        pass

    return best_move

def _get_strict_mandatory_captures(cells: dict, color: str) -> List[Move]:
    """
    Возвращает только СТРОГО обязательные взятия.
    Бий НЕ обязан брать, поэтому его ходы исключаем из списка "принуждений".
    """
    board = Board(cells)
    all_caps = get_all_mandatory_captures(board, color, [])
    strict_caps = []
    for fm, to in all_caps:
        piece_name = cells.get(fm)
        # Оставляем только если атакующая фигура НЕ бий
        if piece_name and _safe_piece_type(piece_name) != "бий":
            strict_caps.append((fm, to))
    return strict_caps