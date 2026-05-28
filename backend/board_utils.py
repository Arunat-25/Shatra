def keys_int_to_str(board_dict: dict) -> dict:
    return {str(k): v for k, v in board_dict.items()}


def keys_str_to_int(board: dict) -> dict:
    return {int(k) if isinstance(k, str) else k: v for k, v in board.items()}


def change_position_name_from_frontend(position: str | int) -> int:
    return position if isinstance(position, int) else int(str(position).replace("position", ""))


def get_starting_board():
    board = {}
    for i in range(1, 63):
        board[i] = None
    # Начальная расстановка (см. game_engine/game_rules.md)
    for i in range(1, 10):
        board[i] = "черная шатра"
    board[10] = "черный бий"
    for i in range(11, 25):
        board[i] = "черная шатра"

    for i in range(54, 63):
        board[i] = "белая шатра"
    board[53] = "белый бий"
    for i in range(39, 53):
        board[i] = "белая шатра"

    return board