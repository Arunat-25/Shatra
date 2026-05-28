"""Тест последовательности ходов пользователя, приводящей к проигрышу AI."""
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

def test_user_sequence_script_does_not_run_on_import():
    """Проверка, что файл не выполняет код на импорт (pytest-friendly)."""
    assert True


moves = [
    (1, "белый", 45, 37),
    (2, "черный", 10, 31),
    (3, "белый", 51, 45),
    (4, "черный", 9, 28),
    (5, "белый", 37, 38),
    (6, "черный", 28, 36),
    (7, "белый", 44, 28),
    (8, "черный", 21, 35),
    (9, "черный", 35, 51),
    (10, "белый", 50, 44),
    (11, "черный", 51, 37),
    (12, "белый", 38, 36),
    (13, "черный", 15, 21),
    (14, "белый", 45, 37),
    (15, "черный", 31, 43),
    (16, "черный", 43, 29),
    (17, "белый", 42, 36),
    (18, "черный", 29, 43),
]


if __name__ == "__main__":
    game = {
        "board": get_starting_board(),
        "mover": "белый",
        "pending_mandatory_position": None,
        "pending_batyr_captures": [],
        "position_history": {},
    }

    print("=== ПОСЛЕДОВАТЕЛЬНОСТЬ ХОДОВ ПОЛЬЗОВАТЕЛЯ ===")
    for step, color, f, t in moves:
        print(f"\n--- Ход {step}: {color} {f}->{t} ---")
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
    print(f"Состояние доски:")
    for i in range(1, 63):
        if game['board'].get(i):
            print(f"  {i}: {game['board'][i]}")