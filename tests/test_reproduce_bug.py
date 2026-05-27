"""Тест ходов после 22 — проверка смены хода после цепочки."""
import sys
sys.path.insert(0, '..')

from game_engine.game_logic import logic
from game_engine.models import GameEvent
from backend.ai import _count_pieces

def get_starting_board():
    board = {}
    for i in range(1, 63):
        board[i] = None
    for i in range(1, 10):
        board[i] = "черная шатра"
    board[10] = "черный бий"
    board[11] = "черный батыр"
    for i in range(12, 25):
        board[i] = "черная шатра"
    for i in range(54, 63):
        board[i] = "белая шатра"
    board[53] = "белый бий"
    for i in range(39, 53):
        board[i] = "белая шатра"
    board[46] = "белый батыр"
    return board

game = {
    "board": get_starting_board(),
    "mover": "белый",
    "pending_mandatory_position": None,
    "pending_batyr_captures": [],
    "position_history": {},
}

moves = [
    (1, "белый", 39, 32),
    (2, "черный", 9, 26),
    (3, "белый", 40, 39),
    (4, "черный", 10, 31),
    (5, "белый", 41, 33),
    (6, "черный", 26, 40),
    (7, "белый", 46, 34),
    (8, "черный", 8, 26),
    (9, "белый", 34, 40),
    (10, "черный", 7, 27),
    (11, "белый", 42, 34),
    (12, "черный", 26, 42),
    (13, "белый", 50, 34),
    (14, "черный", 27, 41),
    (15, "белый", 47, 35),
    (16, "черный", 18, 26),
    (17, "белый", 32, 25),
    (18, "черный", 11, 32),
    (19, "черный", 32, 46),
    (20, "черный", 46, 34),
    (21, "черный", 34, 36),
    (22, "черный", 36, 50),
]

for step, color, f, t in moves:
    print(f"\n=== Ход {step}: {color} {f}->{t} ===")
    print(f"  mover: {game['mover']}, pending: {game.get('pending_mandatory_position')}")
    print(f"  фигура: {game['board'].get(f)}")
    
    result = logic.handle_event(
        GameEvent(
            positions=game["board"],
            mover_color=game["mover"],
            from_pos=f, to_pos=t,
            position_for_mandatory_capture=game.get("pending_mandatory_position"),
        ),
        batyr_captured_this_turn=game.get("pending_batyr_captures"),
        position_history=game.get("position_history", {}),
    )
    
    game["board"] = result.updated_positions
    if result.position_for_mandatory_capture:
        game["pending_mandatory_position"] = result.position_for_mandatory_capture
    else:
        game.pop("pending_mandatory_position", None)
    game["pending_batyr_captures"] = result.captured_pieces or []
    if result.movers_color:
        game["mover"] = result.movers_color
    
    print(f"  msg: {result.message}")
    print(f"  new_mover: {result.movers_color}")
    print(f"  new_pending: {result.position_for_mandatory_capture}")
    print(f"  захваты: {result.captured_positions}")
    print(f"  фигур: {_count_pieces(game['board'])}")

print(f"\n=== ИТОГ ===")
print(f"Ходит: {game['mover']}")
print(f"pending: {game.get('pending_mandatory_position')}")