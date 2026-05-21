def board_to_json(board_dict: dict) -> dict:
    return {str(k): v for k, v in board_dict.items()}


def boards_keys_to_int(board: dict) -> dict:
    return {int(k) if isinstance(k, str) else k: v for k, v in board.items()}


def change_position_name_from_frontend(position: str | int) -> int:
    if isinstance(position, int):
        return position
    if isinstance(position, str):
        return int(position.replace("position", ""))
    return int(position)


def get_starting_board():
    board = {}
    for i in range(1, 63):
        board[i] = None

    for i in range(1, 10):
        board[i] = "черная шатра"
    board[10] = "черный бий"
    board[11] = "черный батыр"
    board[17] = "черный батыр"

    for i in range(54, 63):
        board[i] = "белая шатра"
    board[53] = "белый бий"
    board[46] = "белый батыр"
    board[52] = "белый батыр"

    return board