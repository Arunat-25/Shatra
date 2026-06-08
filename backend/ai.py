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
from backend.ai_geometry import (
    DANGER_ZONE_CELLS,
    SIDE_FILE_CELLS,
    batyr_anchor_cells,
    biy_anchor_cells,
    biy_anchor_factor,
    OPPONENT_MASS_THRESHOLD,
    count_opponent_shatras_in_own_fortress,
    count_own_pieces_in_fortress,
    is_biy_deploy_to_main_field,
    is_fortress_entry,
    is_fortress_shatra_deploy,
    is_main_field_cell,
    main_field_density,
)
from backend.ai_weights import get_active_weights

Move = Tuple[int, int]

# Optional overrides (used by ai_trained)
_TIME_FACTOR = 1.0
_DETERMINISTIC_FALLBACK = False
_TT: dict | None = None
_MAX_MOVES_PER_NODE: int | None = None  # override MAX_MOVES_PER_NODE when set
_MAX_TIME_LIMIT: float | None = None  # strong AI: fixed cap (seconds)


def _w():
    return get_active_weights()


def _pv(pt: str) -> int:
    return _w().piece_values().get(pt, 0)

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
MAX_QUIESCE_TIER3_MOVES = 20
MANDATORY_CAPTURE_CHAIN_DEPTH = 16
HANGING_WITHOUT_GAIN_PENALTY = 500_000

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
    position_history: Optional[dict] = None

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


def _count_color_pieces(cells: dict, color: str) -> int:
    return sum(1 for n in cells.values() if n and _piece_color(n) == color)


def _as_cell_id(cell) -> int:
    return cell if isinstance(cell, int) else int(cell)


def _opponent_has_mass(cells: dict, ai_color: str) -> bool:
    """True when opponent has more than OPPONENT_MASS_THRESHOLD pieces on the board."""
    return _count_color_pieces(cells, _opponent(ai_color)) > OPPONENT_MASS_THRESHOLD


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
    if captured is None or not cells.get(captured):
        return 0, []

    result = process_move(
        copy.deepcopy(cells), color, fm, to,
        chain_capture_cell=None, batyr_captured_this_turn=[], position_history={},
    )
    if not result.updated_positions or result.updated_positions == cells:
        return 0, []

    new_cells = result.updated_positions
    chain = [start_move]
    victim_name = cells.get(captured)
    total_value = _pv(_safe_piece_type(victim_name)) if victim_name else 0
    next_chain = result.position_for_mandatory_capture

    for _ in range(max_depth - 1):
        if not next_chain:
            break
        fm_c = next_chain
        name = new_cells.get(fm_c)
        if not name or _piece_color(name) != color:
            break
        p = Board(new_cells).get_piece_object(fm_c)
        if not p:
            break

        best_step: Tuple[int, Move, dict, Optional[int]] | None = None
        for to_c, ec in shatra_and_biy_possible_captures.get(fm_c, {}).items():
            if new_cells.get(to_c) or not p.can_capture(new_cells, fm_c, to_c, []):
                continue
            v_name = new_cells.get(ec)
            if not v_name:
                continue
            res = process_move(
                copy.deepcopy(new_cells), color, fm_c, to_c,
                chain_capture_cell=fm_c, batyr_captured_this_turn=[], position_history={},
            )
            if not res.updated_positions or res.updated_positions == new_cells:
                continue
            step_val = _pv(_safe_piece_type(v_name))
            cand = (step_val, (fm_c, to_c), res.updated_positions, res.position_for_mandatory_capture)
            if best_step is None or cand[0] > best_step[0]:
                best_step = cand

        if best_step is None:
            break
        step_val, step_move, new_cells, next_chain = best_step
        total_value += step_val
        chain.append(step_move)

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
                    biy_threat = _w().biy_loss_penalty // 2
                elif c_captured:
                    v_name = after_opp.get(c_captured)
                    chain_value += _pv(_safe_piece_type(v_name)) if v_name else 0
            if our_caps:
                best_cap = max(our_caps, key=lambda x: _pv(_safe_piece_type(after_opp.get(x[2]) or "")) if x[2] else 0)
                sim_val, _ = _simulate_capture_sequence(after_opp, ai_color, (best_cap[0], best_cap[1]))
                chain_value = max(chain_value, sim_val)
            best_for_us = max(best_for_us, chain_value + biy_threat)
        if best_for_us > 0:
            return _w().forced_trap_bonus + min(best_for_us, 10_000)
    for opp_fm, opp_to in opp_mandatory:
        opp_p = Board(new_cells).get_piece_object(opp_fm)
        if opp_p:
            opp_cap = find_captured_enemy(new_cells, opp_p, opp_fm, opp_to, [])
            if opp_cap and "бий" in (new_cells.get(opp_cap) or ""):
                return _w().forced_trap_bonus // 2
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
            return _w().chain_capture_bonus + min(value, 5_000)
        return value // 2
    result = process_move(copy.deepcopy(cells), ai_color, fm, to,
                          chain_capture_cell=None, batyr_captured_this_turn=[], position_history={})
    if not result.updated_positions:
        return 0
    new_caps = _get_all_captures_for_color(result.updated_positions, ai_color)
    old_caps = _get_all_captures_for_color(cells, ai_color)
    if len(new_caps) > len(old_caps):
        best_new = max(
            ((_pv(_safe_piece_type(result.updated_positions.get(c[2]) or "")) if c[2] else 0)
            for c in new_caps if c not in old_caps),
            default=0
        )
        return _w().sacrifice_setup_bonus // 2 + best_new // 2
    return 0


def _move_captures_cell(cells: dict, mover: str, fm: int, to: int, target: int) -> bool:
    p = Board(cells).get_piece_object(fm)
    if not p:
        return False
    ec = find_captured_enemy(cells, p, fm, to, [])
    return ec == target


def _evaluate_hanging_sacrifice(state: SearchState, move: Move, ai_color: str) -> int:
    """
    Клетка назначения под боем: соперник выбирает взятие, нам наименее выгодное,
    затем считаем наш ответ по цепочке обязательных взятий (глубоко).
    >0 — жертва оправдана при лучшей защите соперника, иначе штраф.
    """
    fm, to = move
    piece = state.cells.get(fm)
    if not piece or _piece_color(piece) != ai_color:
        return 0
    child, _ = _child_state(state, fm, to)
    if child is None:
        return 0
    opp = _opponent(ai_color)
    if not _is_cell_capturable(child.cells, opp, to):
        return 0
    if child.chain_cell is not None and child.to_move == ai_color:
        return 0

    our_lost = _pv(_safe_piece_type(piece))
    opp_state = SearchState(child.cells, opp)
    nets: List[int] = []

    for opp_move in get_legal_moves(opp_state):
        if not _move_captures_cell(child.cells, opp, opp_move[0], opp_move[1], to):
            continue
        after_opp, _ = _child_state(opp_state, opp_move[0], opp_move[1])
        if after_opp is None:
            continue
        if after_opp.to_move != ai_color:
            nets.append(-our_lost)
            continue
        best_chain = 0
        for cap_move in _get_strict_mandatory_captures(after_opp.cells, ai_color):
            val, _ = _simulate_capture_sequence(
                after_opp.cells, ai_color, cap_move, max_depth=MANDATORY_CAPTURE_CHAIN_DEPTH,
            )
            best_chain = max(best_chain, val)
        nets.append(best_chain - our_lost)

    if not nets:
        return -HANGING_WITHOUT_GAIN_PENALTY
    net = min(nets)
    if net > 0:
        return net
    if net == 0:
        return _w().even_trade_bonus
    return net


FORTRESS_DEPLOY_PENALTY_MIN_SHATRAS = 8


def _count_own_main_field_shatras(cells: dict, ai_color: str) -> int:
    return sum(
        1
        for cell, name in cells.items()
        if name
        and _piece_color(name) == ai_color
        and _safe_piece_type(name) == "шатра"
        and is_main_field_cell(cell)
    )


def _fortress_deploy_penalty_applies(cells: dict, ai_color: str) -> bool:
    """Штраф/фильтр выставления из крепости только при >8 своих шатр на большом поле."""
    return _count_own_main_field_shatras(cells, ai_color) > FORTRESS_DEPLOY_PENALTY_MIN_SHATRAS


def _cells_defended_by_deploy(state: SearchState, after_cells: dict, ai_color: str) -> List[int]:
    """Фигуры на большом поле, которые перестали биться после выставления."""
    opp = _opponent(ai_color)
    defended: List[int] = []
    for cell, name in state.cells.items():
        if not name or _piece_color(name) != ai_color:
            continue
        if not is_main_field_cell(cell):
            continue
        if _is_cell_capturable(state.cells, opp, cell) and not _is_cell_capturable(after_cells, opp, cell):
            defended.append(cell)
    return defended


def _can_defend_cell_with_field_piece(
    state: SearchState,
    ai_color: str,
    threatened_cell: int,
    *,
    exclude_from: int | None = None,
) -> bool:
    """Другая фигура с большого поля может защитить threatened_cell своим ходом."""
    opp = _opponent(ai_color)
    if not _is_cell_capturable(state.cells, opp, threatened_cell):
        return True
    for fm, name in state.cells.items():
        if fm == exclude_from:
            continue
        if not name or _piece_color(name) != ai_color:
            continue
        if not is_main_field_cell(fm):
            continue
        hints = get_hints(
            state.cells,
            ai_color,
            fm,
            batyr_captured_this_turn=state.batyr_captured,
            chain_capture_cell=state.chain_cell,
        )
        for alt_to in (hints.essential_positions or []):
            child, result = _child_state(state, fm, alt_to)
            if child is None:
                continue
            if result.game_over and _we_lost(result, ai_color):
                continue
            defended_piece = child.cells.get(threatened_cell)
            if not defended_piece or _piece_color(defended_piece) != ai_color:
                continue
            if not _is_cell_capturable(child.cells, opp, threatened_cell):
                return True
    return False


def _fortress_deploy_justified(state: SearchState, move: Move, ai_color: str) -> bool:
    """
    Выставление шатры из крепости оправдано, если:
    - взятие;
    - жертва с выгодой по обязательным взятиям;
    - защита висячей фигуры, которую нельзя прикрыть другой фигурой с большого поля.
    """
    fm, to = move
    if not is_fortress_shatra_deploy(fm, to, ai_color):
        return False
    if _evaluate_hanging_sacrifice(state, move, ai_color) > 0:
        return True
    if _is_capture_move(state.cells, ai_color, fm, to):
        return True
    child, _ = _child_state(state, fm, to)
    if child is None:
        return False
    opp = _opponent(ai_color)
    if _is_cell_capturable(child.cells, opp, to):
        return False
    defended = _cells_defended_by_deploy(state, child.cells, ai_color)
    if not defended:
        return False
    for cell in defended:
        if _can_defend_cell_with_field_piece(state, ai_color, cell, exclude_from=fm):
            return False
    return True


def _evaluate_fortress_intrusion(cells: dict, ai_color: str) -> int:
    """Штраф, если соперник ввёл шатру в пустую крепость ИИ."""
    if count_own_pieces_in_fortress(cells, ai_color) > 0:
        return 0
    intruders = count_opponent_shatras_in_own_fortress(cells, ai_color)
    if intruders == 0:
        return 0
    return intruders * _w().fortress_intrusion_penalty


def _fortress_entry_piece_bonus(piece_name: str) -> int:
    if _safe_piece_type(piece_name) != "шатра":
        return 0
    w = _w()
    return min(w.fortress_entry_shatra_bonus, w.piece_shatra - 1)


def _fortress_entry_search_adjustment(state: SearchState, move: Move, ai_color: str) -> int:
    fm, to = move
    mover = state.to_move
    if mover not in (ai_color, _opponent(ai_color)):
        return 0
    piece = state.cells.get(fm)
    if not piece or _piece_color(piece) != mover:
        return 0
    if not is_fortress_entry(fm, to, mover):
        return 0
    bonus = _fortress_entry_piece_bonus(piece)
    if bonus == 0:
        return 0
    if mover == ai_color:
        return bonus
    if count_own_pieces_in_fortress(state.cells, ai_color) == 0:
        return -_w().fortress_intrusion_penalty
    return -bonus


def _fortress_deploy_search_penalty(state: SearchState, move: Move, ai_color: str) -> int:
    """Штраф в minimax: sort key alone не влияет на оценку дерева."""
    fm, to = move
    piece = state.cells.get(fm)
    if not piece or state.to_move != ai_color or _safe_piece_type(piece) != "шатра":
        return 0
    if not is_fortress_shatra_deploy(fm, to, ai_color):
        return 0
    if _fortress_deploy_justified(state, move, ai_color):
        return 0
    if not _fortress_deploy_penalty_applies(state.cells, ai_color):
        return 0
    return _w().fortress_deploy_penalty


def _is_deprioritized_move(state: SearchState, move: Move, ai_color: str) -> bool:
    if state.to_move != ai_color:
        return False
    fm, to = move
    piece = state.cells.get(fm)
    if not piece or _piece_color(piece) != ai_color:
        return False
    pt = _safe_piece_type(piece)
    w = _w()
    if pt == "бий" and main_field_density(state.cells) >= w.crowded_main_field_threshold:
        if is_biy_deploy_to_main_field(fm, to, ai_color):
            return True
    if pt == "шатра" and is_fortress_shatra_deploy(fm, to, ai_color):
        if _fortress_deploy_penalty_applies(state.cells, ai_color):
            if not _fortress_deploy_justified(state, move, ai_color):
                return True
    return False


def _evaluate_biy_threats(cells: dict, ai_color: str) -> int:
    score = 0
    opp = _opponent(ai_color)
    for cell, name in cells.items():
        if not name or _safe_piece_type(name) not in ("шатра", "батыр"):
            continue
        pc = _piece_color(name)
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


def _biy_capture_net_if_recaptured(state: SearchState, move: Move, ai_color: str) -> Optional[int]:
    """
    Бий взял фигуру и встал на `to`. Если соперник заберёт бия на `to` — чистый материал:
    взяли - потеряли бия. None если не взятие бием.
    """
    fm, to = move
    piece = state.cells.get(fm)
    if not piece or _safe_piece_type(piece) != "бий" or state.to_move != ai_color:
        return None
    if not _is_capture_move(state.cells, ai_color, fm, to):
        return None
    victim = _captured_enemy_type(state.cells, ai_color, fm, to)
    if victim == "бий":
        return WIN_SCORE
    child, res = _child_state(state, fm, to)
    if child is None:
        return None
    if res.game_over and _we_won(res, ai_color):
        return WIN_SCORE
    gained = _pv(victim) if victim else 0
    if not _is_cell_capturable(child.cells, _opponent(ai_color), to):
        return gained
    return gained - _w().piece_biy

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

    w = _w()
    score = 0
    opp = _opponent(ai_color)
    our_biy = _find_biy_cell(cells, ai_color)
    enemy_biy = _find_biy_cell(cells, opp)
    density = main_field_density(cells)
    opp_mass = _opponent_has_mass(cells, ai_color)

    for cell, name in cells.items():
        if not name:
            continue
        cell_id = _as_cell_id(cell)
        color = _piece_color(name)
        pt = _safe_piece_type(name)
        sign = 1 if color == ai_color else -1
        score += sign * _pv(pt)
        idx = _mirror_cell(cell_id) if color == "черный" else cell_id
        on_danger = (
            opp_mass
            and color == ai_color
            and cell_id in DANGER_ZONE_CELLS
        )

        if pt == "шатра":
            score += sign * _shatra_promotion_progress(color, cell_id) * w.promotion_progress_weight
            if _clear_promotion_path(cells, color, cell_id):
                score += sign * 50
            promo = WHITE_PROMOTION if color == "белый" else BLACK_PROMOTION
            if cell_id in promo:
                score += sign * w.promotion_bonus
        elif pt == "бий":
            if not on_danger:
                score += sign * BIY_TABLE[idx] * w.position_scale
            if cell_id in biy_anchor_cells(color):
                k = biy_anchor_factor(density, w.crowded_main_field_threshold)
                score += sign * int(w.biy_anchor_bonus * k)
        elif pt == "батыр":
            if cell_id in batyr_anchor_cells(color) and not _is_cell_capturable(cells, _opponent(color), cell_id):
                score += sign * w.batyr_anchor_bonus
            elif (
                opp_mass
                and cell_id in SIDE_FILE_CELLS
                and not _is_cell_capturable(cells, _opponent(color), cell_id)
            ):
                score += sign * w.side_file_batyr_bonus

        if (
            opp_mass
            and pt == "шатра"
            and cell_id in SIDE_FILE_CELLS
            and not _is_cell_capturable(cells, _opponent(color), cell_id)
        ):
            score += sign * w.side_file_shatra_bonus

        if on_danger:
            score -= w.danger_zone_penalty

    if our_biy and _is_cell_capturable(cells, opp, our_biy):
        score -= w.biy_loss_penalty
    if enemy_biy and _is_cell_capturable(cells, ai_color, enemy_biy):
        score += w.biy_loss_penalty // 2

    for cell, name in cells.items():
        if not name or _piece_color(name) != ai_color:
            continue
        pt = _safe_piece_type(name)
        if pt == "бий":
            continue
        if _is_cell_capturable(cells, opp, cell):
            score -= w.hanging_penalty + _pv(pt) // 2

    score += _evaluate_biy_threats(cells, ai_color)
    score -= _evaluate_fortress_intrusion(cells, ai_color)

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
                            score -= w.biy_loss_penalty // 3

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

def _pick_best_mandatory_capture_fork(state: SearchState, ai_color: str) -> Optional[Move]:
    """Выбор между несколькими обязательными взятиями: длиннее своя цепочка — лучше."""
    if state.to_move != ai_color or state.chain_cell is not None:
        return None
    strict = _get_strict_mandatory_captures(state.cells, ai_color)
    if len(strict) < 2:
        return None
    legal = set(get_legal_moves(state))
    options = [m for m in strict if m in legal]
    if len(options) < 2:
        return None
    best_move: Optional[Move] = None
    best_score = -math.inf
    for move in options:
        chain_val, chain = _simulate_capture_sequence(
            state.cells, ai_color, move, max_depth=MANDATORY_CAPTURE_CHAIN_DEPTH,
        )
        score = chain_val * 100 + len(chain) * 1_000
        if score > best_score:
            best_score = score
            best_move = move
    return best_move


def _mandatory_capture_chain_bonus(state: SearchState, move: Move, ai_color: str) -> int:
    """Бонус только при выборе между вилками обязательных взятий (не в продолжении цепочки)."""
    if state.chain_cell is not None:
        return 0
    if state.to_move != ai_color or move not in _mandatory_moves_set(state):
        return 0
    chain_val, chain = _simulate_capture_sequence(
        state.cells, ai_color, move, max_depth=MANDATORY_CAPTURE_CHAIN_DEPTH,
    )
    return chain_val * 40 + len(chain) * 2_000


def _repetition_move_adjustment(
    state: SearchState, move: Move, ai_color: str, child_cells: dict,
) -> int:
    """При перевесе не зацикливаться; при минусе — можно тянуть к ничьей."""
    hist = state.position_history
    if not hist or state.to_move != ai_color:
        return 0
    key = str(sorted(child_cells.items()))
    seen = hist.get(key, 0)
    if seen < 1:
        return 0
    material = evaluate(child_cells, ai_color)
    if material > 400:
        return -120_000
    if material < -400:
        return 12_000
    return -20_000


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

    if ptype == "бий" and state.to_move == ai_color:
        biy_net = _biy_capture_net_if_recaptured(state, move, ai_color)
        if biy_net is not None and biy_net < 0:
            return -950_000
        if biy_net is not None and biy_net >= WIN_SCORE // 2:
            return biy_net

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
            score += _w().promotion_bonus * 2
        score += _shatra_promotion_progress(ai_color, to) * 2

    # ❗ КРИТИЧЕСКИЙ ФИКС: Если Бий делает ход и оказывается под боем — жёстко запрещаем
    # Раньше было score -= 50_000, но это перекрывалось бонусами за взятие (+1_200 / +2_500)
    # Теперь возвращаем -950_000 сразу — это гарантированно ниже любого тактического бонуса
    if ptype == "бий" and state.to_move == ai_color:
        if _is_cell_capturable(child.cells, _opponent(ai_color), to):
            return -950_000

    # ❗ ТАКТИЧЕСКИЕ БОНУСЫ / ШТРАФЫ
    if state.to_move == ai_color:
        if _creates_mandatory_capture_for_opp(cells, ai_color, move):
            score -= 50_000
        score += _evaluate_chain_potential(cells, ai_color, move) // 2
        score += _mandatory_capture_chain_bonus(state, move, ai_color)
        sac = _evaluate_hanging_sacrifice(state, move, ai_color)
        if sac <= -HANGING_WITHOUT_GAIN_PENALTY // 2:
            return sac
        if sac > 0:
            score += sac
        elif (
            _is_cell_capturable(child.cells, _opponent(ai_color), to)
            and not (child.chain_cell is not None and child.to_move == ai_color)
        ):
            return -HANGING_WITHOUT_GAIN_PENALTY
        w = _w()
        k = biy_anchor_factor(main_field_density(cells), w.crowded_main_field_threshold)
        opp_mass = _opponent_has_mass(cells, ai_color)
        if (
            opp_mass
            and ptype == "шатра"
            and to in SIDE_FILE_CELLS
            and not _is_cell_capturable(child.cells, _opponent(ai_color), to)
        ):
            score += w.side_file_shatra_bonus
        elif ptype == "батыр" and to in batyr_anchor_cells(ai_color) and not _is_cell_capturable(child.cells, _opponent(ai_color), to):
            score += w.batyr_anchor_bonus
        elif (
            opp_mass
            and ptype == "батыр"
            and to in SIDE_FILE_CELLS
            and not _is_cell_capturable(child.cells, _opponent(ai_color), to)
        ):
            score += w.side_file_batyr_bonus
        elif ptype == "бий" and to in biy_anchor_cells(ai_color):
            if not (main_field_density(cells) >= w.crowded_main_field_threshold and is_biy_deploy_to_main_field(fm, to, ai_color)):
                score += int(w.biy_anchor_bonus * k)
        if opp_mass and to in DANGER_ZONE_CELLS:
            score -= w.danger_zone_penalty
        if ptype == "шатра" and is_fortress_entry(fm, to, ai_color):
            score += _fortress_entry_piece_bonus(piece)
        if (
            ptype == "шатра"
            and is_fortress_shatra_deploy(fm, to, ai_color)
            and _fortress_deploy_penalty_applies(cells, ai_color)
            and not _fortress_deploy_justified(state, move, ai_color)
        ):
            score -= w.fortress_deploy_penalty
        score += _repetition_move_adjustment(state, move, ai_color, child.cells)

    return score

def _effective_max_moves_per_node() -> int:
    if _MAX_MOVES_PER_NODE is not None:
        return _MAX_MOVES_PER_NODE
    return MAX_MOVES_PER_NODE


def _time_exceeded(start_time: float | None, time_limit: float) -> bool:
    return start_time is not None and time.time() - start_time > time_limit


def _count_batyrs_for_color(cells: dict, color: str) -> int:
    return sum(
        1 for n in cells.values()
        if n and "батыр" in n and _piece_color(n) == color
    )


def _mandatory_moves_set(state: SearchState) -> set:
    board = Board(state.cells)
    return set(get_all_mandatory_captures(board, state.to_move, state.batyr_captured))


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


def _is_must_search_move(
    state: SearchState,
    move: Move,
    ai_color: str,
    mandatory: set,
) -> bool:
    if move in mandatory:
        return True
    if state.chain_cell is not None:
        return True
    fm, to = move
    if _captured_enemy_type(state.cells, state.to_move, fm, to) == "бий":
        child, result = _child_state(state, move[0], move[1])
        if child is not None and result.game_over and _we_won(result, ai_color):
            return True
    return False


def _is_tactical_secondary_move(state: SearchState, move: Move, ai_color: str) -> bool:
    fm, to = move
    if _is_capture_move(state.cells, state.to_move, fm, to):
        return True
    # Defensive priority: if we are the AI to move and this move reduces the number
    # of our hanging non-biy pieces, treat it as tactical so it is searched early.
    if state.to_move == ai_color:
        opp = _opponent(ai_color)
        before = 0
        for c, name in state.cells.items():
            if not name or _piece_color(name) != ai_color:
                continue
            if _safe_piece_type(name) == "бий":
                continue
            if _is_cell_capturable(state.cells, opp, c):
                before += 1
        if before:
            child, _ = _child_state(state, fm, to)
            if child is not None:
                after = 0
                for c, name in child.cells.items():
                    if not name or _piece_color(name) != ai_color:
                        continue
                    if _safe_piece_type(name) == "бий":
                        continue
                    if _is_cell_capturable(child.cells, opp, c):
                        after += 1
                if after < before:
                    return True
    return _is_quiescence_move(state, move, ai_color)


def _move_limit(state: SearchState, maximizing: bool) -> int:
    limit = _effective_max_moves_per_node()
    if _count_batyrs_for_color(state.cells, state.to_move) > 0:
        limit += 8
    return limit


def _select_moves_for_search(
    state: SearchState,
    moves: List[Move],
    ai_color: str,
    maximizing: bool,
    start_time: float | None = None,
    time_limit: float = math.inf,
    tier3_cap: int | None = None,
) -> List[Move]:
    """Tier1 (must) + Tier2 (tactical) + capped Tier3 — never drop mandatory captures."""
    if not moves:
        return moves
    if len(moves) > 24 and _time_exceeded(start_time, time_limit):
        mandatory = _mandatory_moves_set(state)
        return [m for m in moves if _is_must_search_move(state, m, ai_color, mandatory)]

    mandatory = _mandatory_moves_set(state)
    tier1: List[Move] = []
    tier2: List[Move] = []
    tier3: List[Move] = []
    seen: set = set()

    for move in moves:
        if move in seen:
            continue
        if _is_must_search_move(state, move, ai_color, mandatory):
            tier1.append(move)
            seen.add(move)
        elif _is_tactical_secondary_move(state, move, ai_color):
            tier2.append(move)
            seen.add(move)
        else:
            tier3.append(move)

    sort_color = ai_color if maximizing else _opponent(ai_color)
    tier2.sort(key=lambda m: _move_sort_key(state, m, sort_color), reverse=True)
    tier3.sort(key=lambda m: _move_sort_key(state, m, sort_color), reverse=True)

    cap = tier3_cap if tier3_cap is not None else _move_limit(state, maximizing)
    return tier1 + tier2 + tier3[:cap]


def _filter_moves_for_ai(state, moves, ai_color):
    if state.to_move != ai_color:
        return moves
    safe = []
    for move in moves:
        if _is_deprioritized_move(state, move, ai_color):
            continue
        child, result = _child_state(state, move[0], move[1])
        if child is None:
            continue
        if result.game_over and _we_won(result, ai_color):
            safe.append(move)
            continue
        if _move_exposes_biy(state, move, ai_color):
            continue
        piece = state.cells.get(move[0])
        if piece and _safe_piece_type(piece) == "бий":
            biy_net = _biy_capture_net_if_recaptured(state, move, ai_color)
            if biy_net is not None and biy_net < 0:
                continue
        fm, to = move
        own_chain = child.chain_cell is not None and child.to_move == ai_color
        if _is_cell_capturable(child.cells, _opponent(ai_color), to) and not own_chain:
            if _evaluate_hanging_sacrifice(state, move, ai_color) <= 0:
                continue
        if _creates_mandatory_capture_for_opp(state.cells, ai_color, move):
            if _evaluate_hanging_sacrifice(state, move, ai_color) <= 0:
                continue
        safe.append(move)
    if safe:
        return safe
    ranked = sorted(moves, key=lambda m: _move_sort_key(state, m, ai_color), reverse=True)
    return ranked[: max(3, len(ranked) // 3)]

def _ordered_moves(
    state,
    ai_color,
    maximizing,
    start_time=None,
    time_limit=math.inf,
):
    moves = get_legal_moves(state)
    if not moves:
        return moves
    if maximizing:
        moves = _filter_moves_for_ai(state, moves, ai_color)
    return _select_moves_for_search(
        state, moves, ai_color, maximizing, start_time, time_limit,
    )

def quiescence(state, alpha, beta, maximizing, ai_color, depth=0, start_time=None, time_limit=math.inf):
    # Quiescence never reads or writes transposition table (_TT).
    if _time_exceeded(start_time, time_limit):
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

    q_cap = _move_limit(state, maximizing) + MAX_QUIESCE_TIER3_MOVES
    tactical = _select_moves_for_search(
        state, tactical, ai_color, maximizing, start_time, time_limit, tier3_cap=q_cap,
    )

    for move in tactical:
        if _time_exceeded(start_time, time_limit):
            return stand
        child, result = _child_state(state, move[0], move[1])
        if child is None:
            continue

        moving_piece = state.cells.get(move[0])
        is_biy_move = moving_piece and "бий" in moving_piece
        extra_depth = 1 if is_biy_move else 0

        terminal = _terminal_score(result, ai_color)
        if terminal is not None:
            val = terminal
        else:
            next_max = child.to_move == ai_color
            mandatory_chain = (
                state.chain_cell is not None
                or child.chain_cell is not None
                or _is_capture_move(state.cells, state.to_move, move[0], move[1])
            )
            if mandatory_chain:
                next_depth = depth + 1
            else:
                next_depth = min(depth + 1 + extra_depth, MAX_QUIESCE_DEPTH + 2)
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

def _tt_key(state: SearchState, depth: int, maximizing: bool, ai_color: str):
    items = tuple(sorted((k, v) for k, v in state.cells.items()))
    return (items, state.to_move, state.chain_cell, tuple(state.batyr_captured), depth, maximizing, ai_color)


def minimax(state, depth, alpha, beta, maximizing, ai_color, start_time=None, time_limit=math.inf):
    if depth >= 1 and _TT is not None:
        key = _tt_key(state, depth, maximizing, ai_color)
        cached = _TT.get(key)
        if cached is not None:
            return cached
    if _time_exceeded(start_time, time_limit):
        return evaluate(state.cells, ai_color), None
    over, winner_color, _draw = is_game_over(Board(state.cells))
    if over and winner_color:
        return evaluate(state.cells, ai_color), None
    if depth == 0:
        val = quiescence(state, alpha, beta, maximizing, ai_color, start_time=start_time, time_limit=time_limit)
        return val, None

    current_depth = depth
    if not maximizing and state.to_move == ai_color:
        moves = get_legal_moves(state)
        has_chain = any(_evaluate_chain_potential(state.cells, ai_color, m) > 0 for m in moves[:5])
        if has_chain:
            current_depth = min(depth + 1, depth + 2)

    moves = _ordered_moves(state, ai_color, maximizing, start_time, time_limit)
    if not moves:
        return (LOSE_SCORE if maximizing else WIN_SCORE), None

    best_move, best_val = (None, -math.inf) if maximizing else (None, math.inf)

    if maximizing:
        for move in moves:
            if _time_exceeded(start_time, time_limit):
                if best_move is not None:
                    return best_val, best_move
                return evaluate(state.cells, ai_color), None
            child, result = _child_state(state, move[0], move[1])
            if child is None:
                continue
            terminal = _terminal_score(result, ai_color)
            val = terminal if terminal is not None else minimax(child, current_depth - 1, alpha, beta, child.to_move == ai_color, ai_color, start_time, time_limit)[0]
            if state.to_move == ai_color:
                val -= _fortress_deploy_search_penalty(state, move, ai_color)
                val += _mandatory_capture_chain_bonus(state, move, ai_color)
            val += _fortress_entry_search_adjustment(state, move, ai_color)
            if val > best_val:
                best_val, best_move = val, move
            alpha = max(alpha, val)
            if beta <= alpha:
                break
        result = (best_val, best_move)
        if depth >= 1 and _TT is not None:
            _TT[_tt_key(state, depth, maximizing, ai_color)] = result
        return result
    else:
        for move in moves:
            if _time_exceeded(start_time, time_limit):
                if best_move is not None:
                    return best_val, best_move
                return evaluate(state.cells, ai_color), None
            child, result = _child_state(state, move[0], move[1])
            if child is None:
                continue
            terminal = _terminal_score(result, ai_color)
            val = terminal if terminal is not None else minimax(child, current_depth - 1, alpha, beta, child.to_move == ai_color, ai_color, start_time, time_limit)[0]
            val += _fortress_entry_search_adjustment(state, move, ai_color)
            if val < best_val:
                best_val, best_move = val, move
            beta = min(beta, val)
            if beta <= alpha:
                break
        result = (best_val, best_move)
        if depth >= 1 and _TT is not None:
            _TT[_tt_key(state, depth, maximizing, ai_color)] = result
        return result

def _get_time_limit(cells: dict) -> float:
    if _MAX_TIME_LIMIT is not None:
        return _MAX_TIME_LIMIT
    n = _count_pieces(cells)
    for thr, lim in AI_TIME_LIMITS:
        if n > thr:
            return lim * _TIME_FACTOR
    return 1.2 * _TIME_FACTOR

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

def get_best_move(
    cells: dict,
    ai_color: str,
    depth: int = 3,
    batyr_captured_this_turn=None,
    chain_capture_cell=None,
    position_history: dict | None = None,
) -> Optional[Move]:
    if not cells:
        return None
    state = SearchState(
        cells=cells,
        to_move=ai_color,
        chain_cell=chain_capture_cell,
        batyr_captured=list(batyr_captured_this_turn or []),
        position_history=position_history,
    )
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
    fork = _pick_best_mandatory_capture_fork(state, ai_color)
    if fork is not None:
        return fork

    n = _count_pieces(cells)
    time_limit = _get_time_limit(cells)
    
    # ❗ Больше времени на тактику
    has_tactical = any(_evaluate_chain_potential(cells, ai_color, m) > 0 or 
                       _creates_mandatory_capture_for_opp(cells, ai_color, m)
                       for m in get_legal_moves(state)[:10])
    if has_tactical:
        tactical_cap = _MAX_TIME_LIMIT if _MAX_TIME_LIMIT is not None else 3.0
        time_limit = min(time_limit * 1.5, tactical_cap)

    max_depth = depth

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
            if _DETERMINISTIC_FALLBACK or len(top_moves) == 1:
                best_move = moves[0]
            else:
                best_move = random.choice(top_moves)

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