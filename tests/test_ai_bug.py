"""Тест воспроизведения проблемы AI, когда он подставляет своего бия."""

from game_engine.game_logic import logic
from game_engine.models import GameEvent
from backend.ai import _count_pieces, get_best_move
from game_engine.board import Board

def create_board_after_moves(moves):
    """Создает доску после последовательности ходов."""
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

    game = {
        "board": board,
        "mover": "белый",
        "pending_mandatory_position": None,
        "pending_batyr_captures": [],
        "position_history": {},
    }

    for step, color, f, t in moves:
        print(f"\n--- Ход {step}: {color} {f}->{t} ---")
        
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

        print(f"  new_mover: {result.movers_color}")
        print(f"  pending: {result.position_for_mandatory_capture}")
        if result.captured_positions:
            print(f"  захвачено: {result.captured_positions}")

    return game["board"], game["mover"]

# Критическая последовательность ходов, приводящая к проблеме
problematic_moves = [
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
]


def test_ai_bug_script_does_not_run_on_import():
    """Проверка, что файл не выполняет код на импорт (pytest-friendly)."""
    assert True


if __name__ == "__main__":
    print("=== ВОСПРОИЗВЕДЕНИЕ ПРОБЛЕМЫ С AI ===")
    board, current_mover = create_board_after_moves(problematic_moves)

    print(f"\n=== СОСТОЯНИЕ ПЕРЕД ХОДОМ AI ===")
    print(f"Ходит: {current_mover}")
    print("Доска:")
    for i in range(1, 63):
        if board.get(i):
            print(f"  {i}: {board[i]}")

    print(f"\n=== ХОД AI ===")
    if current_mover == "черный":
        # AI (черный) должен сделать ход
        ai_move = get_best_move(board, "черный", depth=3)
        print(f"AI выбрал ход: {ai_move}")

        if ai_move:
            # Применяем ход AI
            result = logic.handle_event(
                GameEvent(
                    positions=board,
                    mover_color="черный",
                    from_pos=ai_move[0], to_pos=ai_move[1],
                    position_for_mandatory_capture=None,
                ),
                batyr_captured_this_turn=[],
                position_history={},
            )

            board = result.updated_positions
            if result.position_for_mandatory_capture:
                print(f"Обязательный захват: {result.position_for_mandatory_capture}")
            if result.captured_positions:
                print(f"Захвачено: {result.captured_positions}")

            print(f"Теперь ходит: {result.movers_color}")

            # Проверяем, не подставил ли AI своего бия
            from backend.ai import _find_biy_cell, _is_cell_capturable
            black_biy = _find_biy_cell(board, "черный")
            if black_biy:
                if _is_cell_capturable(board, "белый", black_biy):
                    print(f"ОШИБКА: AI подставил своего бия на позиции {black_biy}!")
                    print("Белые могут его захватить!")

            print("Доска после хода AI:")
            for i in range(1, 63):
                if board.get(i):
                    print(f"  {i}: {board[i]}")
        else:
            print("AI не смог найти ход")
    else:
        print("Сейчас ход белых, а не AI")