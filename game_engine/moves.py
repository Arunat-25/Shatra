from typing import List, Tuple, Optional
import copy

from game_engine.board import Board
from game_engine.models import GameEventResult
from game_engine.endgame import is_game_over
from game_engine.message_codes import (
    TURN_NOW,
    MOVE_PASSED,
    CAPTURE_CONTINUE,
    CAPTURE_CONTINUE_SAME,
    CAPTURE_MUST,
    CAPTURE_MUST_CONTINUE,
    MOVE_UNKNOWN_PIECE,
    MOVE_NO_CAPTURE_TARGET,
    MOVE_TARGET_OCCUPIED,
    PIECE_PROMOTED,
    VALIDATION_TO_MESSAGE,
)
from game_engine.validation import (
    get_all_mandatory_captures,
    batyr_can_continue_capture,
    find_captured_enemy,
    validate_move_with_code,
)
from game_engine.dictionaries import shatra_and_biy_possible_captures

PROMOTION_FOR_WHITE = {1, 2, 3}
PROMOTION_FOR_BLACK = {60, 61, 62}


def _promote_shatra(cells: dict, cell: int, color: str) -> bool:
    cell_name = cells.get(cell)
    if not cell_name or "шатра" not in cell_name:
        return False
    if color == "белый" and cell in PROMOTION_FOR_WHITE:
        cells[cell] = "белый батыр"
        return True
    if color == "черный" and cell in PROMOTION_FOR_BLACK:
        cells[cell] = "черный батыр"
        return True
    return False


def execute_move(
    cells: dict,
    from_cell: int,
    to_cell: int,
    current_color: str,
    batyr_captured_this_turn: List[int] = None,
) -> Tuple[dict, List[int], List[int]]:
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []

    new_cells = copy.deepcopy(cells)
    board = Board(new_cells)
    captured_positions = []
    new_batyr_captures = copy.copy(batyr_captured_this_turn)

    piece = board.get_piece_object(from_cell)

    if piece and piece.can_capture(cells, from_cell, to_cell, batyr_captured_this_turn):
        enemy_cell = find_captured_enemy(cells, piece, from_cell, to_cell, batyr_captured_this_turn)
        board.move_piece(from_cell, to_cell)
        if enemy_cell:
            board.remove_piece(enemy_cell)
            captured_positions.append(enemy_cell)
            if piece.get_type() == "батыр":
                new_batyr_captures.append(enemy_cell)
        return board.copy_cells(), captured_positions, new_batyr_captures

    board.move_piece(from_cell, to_cell)
    if piece and piece.get_type() == "батыр":
        new_batyr_captures.clear()
    return board.copy_cells(), captured_positions, new_batyr_captures


def _game_over_result(
    positions: dict,
    *,
    winner_color: str | None = None,
    draw_reason: str | None = None,
    captured_positions: List[int] | None = None,
    captured_pieces: List[int] | None = None,
) -> GameEventResult:
    return GameEventResult(
        movers_color=None,
        updated_positions=positions,
        game_over=True,
        winner_color=winner_color,
        draw_reason=draw_reason,
        captured_positions=captured_positions or [],
        captured_pieces=captured_pieces or [],
    )


def _validation_error(code: str) -> GameEventResult:
    message_code = VALIDATION_TO_MESSAGE.get(code, "move.illegal")
    return GameEventResult(message_code=message_code)


def process_move(
    cells: dict,
    current_color: str,
    from_cell: int,
    to_cell: int,
    chain_capture_cell: int = None,
    batyr_captured_this_turn: List[int] = None,
    position_history: dict = None,
    moves_with_two_biys: int = 0,
) -> GameEventResult:
    if batyr_captured_this_turn is None:
        batyr_captured_this_turn = []
    if position_history is None:
        position_history = {}

    current_batyr_captures = copy.copy(batyr_captured_this_turn)
    board_copy = copy.deepcopy(cells)

    board_obj = Board(board_copy)
    over, winner_color, draw_reason = is_game_over(board_obj, position_history, moves_with_two_biys)
    if over:
        return _game_over_result(cells, winner_color=winner_color, draw_reason=draw_reason)

    if chain_capture_cell == 0:
        over, winner_color, draw_reason = is_game_over(
            Board(board_copy), position_history, moves_with_two_biys,
        )
        return _finish_move(
            positions=board_copy,
            mover_color=current_color,
            message_code=MOVE_PASSED,
            history=True,
            clear_pending=True,
            game_over=over,
            winner_color=winner_color,
            draw_reason=draw_reason,
        )

    if chain_capture_cell is not None and chain_capture_cell != 0:
        return _process_chain_capture(
            board_copy, cells, current_color, from_cell, to_cell,
            chain_capture_cell, current_batyr_captures, position_history, moves_with_two_biys,
        )

    if chain_capture_cell is None or chain_capture_cell == 0:
        valid, _error_msg, code = validate_move_with_code(
            board_copy, from_cell, to_cell, current_color, current_batyr_captures,
        )
        if not valid:
            return _validation_error(code)

    new_cells, captured_positions, new_batyr_captures = execute_move(
        board_copy, from_cell, to_cell, current_color, current_batyr_captures,
    )

    piece = Board(board_copy).get_piece_object(from_cell)
    if piece is None:
        piece = Board(board_copy).get_piece_object(to_cell)
    piece_kind = piece.get_type() if piece else ""

    if piece_kind == "шатра":
        if _promote_shatra(new_cells, to_cell, current_color):
            if not captured_positions:
                return _finish_move(
                    positions=new_cells,
                    mover_color=current_color,
                    message_code=PIECE_PROMOTED,
                    message_params={"color": current_color},
                    history=True,
                    clear_pending=True,
                    captured_positions=captured_positions,
                )
            piece_kind = "батыр"

    next_board = Board(new_cells)
    over, winner_color, draw_reason = is_game_over(next_board, position_history, moves_with_two_biys)
    if over:
        return _game_over_result(
            new_cells,
            winner_color=winner_color,
            draw_reason=draw_reason,
            captured_positions=captured_positions,
        )

    has_captured = len(captured_positions) > 0
    can_continue_chain = False
    if has_captured:
        if piece_kind in ["шатра", "бий"]:
            piece_at_land = Board(new_cells).get_piece_object(to_cell)
            if piece_at_land:
                for to_cell_next in shatra_and_biy_possible_captures.get(to_cell, {}):
                    if piece_at_land.can_capture(new_cells, to_cell, to_cell_next, new_batyr_captures):
                        can_continue_chain = True
                        break
        else:
            can_continue_chain = batyr_can_continue_capture(
                next_board, to_cell, current_color, new_batyr_captures,
            )

    can_pass_turn = piece_kind == "бий" and has_captured

    if can_continue_chain:
        return GameEventResult(
            message_code=CAPTURE_CONTINUE,
            movers_color=current_color,
            updated_positions=new_cells,
            captured_positions=captured_positions,
            opportunity_pass_the_move=can_pass_turn,
            position_for_mandatory_capture=to_cell,
            captured_pieces=new_batyr_captures,
        )

    if has_captured and not can_continue_chain:
        next_player = _opponent(current_color)
        over, winner_color, draw_reason = is_game_over(next_board, position_history, moves_with_two_biys)
        return _finish_move(
            positions=new_cells,
            mover_color=current_color,
            message_code=TURN_NOW,
            message_params={"color": next_player},
            history=True,
            clear_pending=True,
            game_over=over,
            winner_color=winner_color,
            draw_reason=draw_reason,
            captured_positions=captured_positions,
            captured_pieces=new_batyr_captures,
            opportunity_pass=can_pass_turn,
        )

    next_player = _opponent(current_color)
    over, winner_color, draw_reason = is_game_over(next_board, position_history, moves_with_two_biys)

    chain_capture_pos = None
    if next_player and not over:
        mandatory_captures = get_all_mandatory_captures(Board(new_cells), next_player)
        if mandatory_captures:
            chain_capture_pos = mandatory_captures[0][0]

    return _finish_move(
        positions=new_cells,
        mover_color=current_color,
        message_code=TURN_NOW,
        message_params={"color": next_player},
        history=True,
        clear_pending=True,
        game_over=over,
        winner_color=winner_color,
        draw_reason=draw_reason,
        captured_positions=captured_positions,
        opportunity_pass=can_pass_turn,
        mandatory_pos=chain_capture_pos,
    )


def _process_chain_capture(
    board_copy, cells, current_color, from_cell, to_cell,
    chain_capture_cell, current_batyr_captures, position_history=None, moves_with_two_biys=0,
) -> GameEventResult:
    if from_cell != chain_capture_cell:
        return GameEventResult(
            message_code=CAPTURE_CONTINUE_SAME,
            movers_color=current_color,
            updated_positions=cells,
        )
    piece = Board(board_copy).get_piece_object(from_cell)
    if piece and piece.get_type() in ["шатра", "бий"]:
        return _process_chain_shatra_biy(
            board_copy, cells, current_color, from_cell, to_cell,
            current_batyr_captures, piece, position_history, moves_with_two_biys,
        )
    if piece and piece.get_type() == "батыр":
        return _process_chain_batyr(
            board_copy, cells, current_color, from_cell, to_cell,
            current_batyr_captures, piece, position_history, moves_with_two_biys,
        )
    return GameEventResult(
        message_code=MOVE_UNKNOWN_PIECE,
        movers_color=current_color,
        updated_positions=cells,
    )


def _process_chain_shatra_biy(
    board_copy, cells, current_color, from_cell, to_cell,
    current_batyr_captures, piece, position_history=None, moves_with_two_biys=0,
) -> GameEventResult:
    if not piece.can_capture(board_copy, from_cell, to_cell, current_batyr_captures):
        return GameEventResult(
            message_code=CAPTURE_MUST,
            movers_color=current_color,
            updated_positions=cells,
        )

    new_cells, captured_positions, new_batyr_captures = execute_move(
        board_copy, from_cell, to_cell, current_color, current_batyr_captures,
    )
    _promote_shatra(new_cells, to_cell, current_color)
    board = Board(new_cells)
    piece_kind = piece.get_type()

    over, winner_color, draw_reason = is_game_over(board, position_history, moves_with_two_biys)
    if over:
        return _game_over_result(
            new_cells,
            winner_color=winner_color,
            draw_reason=draw_reason,
            captured_positions=captured_positions,
            captured_pieces=new_batyr_captures,
        )

    can_continue_chain = False
    piece_at_land = board.get_piece_object(to_cell)
    if piece_at_land:
        if piece_at_land.get_type() == "батыр":
            can_continue_chain = batyr_can_continue_capture(
                board, to_cell, current_color, new_batyr_captures,
            )
        else:
            for to_cell_next in shatra_and_biy_possible_captures.get(to_cell, {}):
                if piece_at_land.can_capture(new_cells, to_cell, to_cell_next, new_batyr_captures):
                    can_continue_chain = True
                    break

    can_pass_turn = piece_kind == "бий"

    if can_continue_chain:
        return GameEventResult(
            message_code=CAPTURE_CONTINUE,
            movers_color=current_color,
            updated_positions=new_cells,
            captured_positions=captured_positions,
            opportunity_pass_the_move=can_pass_turn,
            position_for_mandatory_capture=to_cell,
            captured_pieces=new_batyr_captures,
        )

    next_player = _opponent(current_color)
    return _finish_move(
        positions=new_cells,
        mover_color=current_color,
        message_code=TURN_NOW,
        message_params={"color": next_player},
        history=True,
        clear_pending=True,
        captured_positions=captured_positions,
        opportunity_pass=can_pass_turn,
    )


def _process_chain_batyr(
    board_copy, cells, current_color, from_cell, to_cell,
    current_batyr_captures, piece, position_history=None, moves_with_two_biys=0,
) -> GameEventResult:
    if not piece.can_capture(board_copy, from_cell, to_cell, current_batyr_captures):
        return GameEventResult(
            message_code=CAPTURE_MUST_CONTINUE,
            movers_color=current_color,
            updated_positions=cells,
        )

    new_cells, captured_positions, new_batyr_captures = execute_move(
        board_copy, from_cell, to_cell, current_color, current_batyr_captures,
    )
    board = Board(new_cells)

    over, winner_color, draw_reason = is_game_over(board, position_history, moves_with_two_biys)
    if over:
        return _game_over_result(
            new_cells,
            winner_color=winner_color,
            draw_reason=draw_reason,
            captured_positions=captured_positions,
        )

    can_continue = batyr_can_continue_capture(board, to_cell, current_color, new_batyr_captures)

    if can_continue:
        return GameEventResult(
            message_code=CAPTURE_CONTINUE,
            movers_color=current_color,
            updated_positions=new_cells,
            captured_positions=captured_positions,
            position_for_mandatory_capture=to_cell,
            captured_pieces=new_batyr_captures,
        )

    next_player = _opponent(current_color)
    return _finish_move(
        positions=new_cells,
        mover_color=current_color,
        message_code=TURN_NOW,
        message_params={"color": next_player},
        history=True,
        clear_pending=True,
        captured_positions=captured_positions,
        captured_pieces=new_batyr_captures,
    )


def _finish_move(
    positions: dict,
    mover_color: str,
    message_code: str = "",
    message_params: dict | None = None,
    history: bool = False,
    clear_pending: bool = False,
    game_over: bool = False,
    winner_color: str | None = None,
    draw_reason: str | None = None,
    captured_positions: List[int] | None = None,
    opportunity_pass: bool = False,
    mandatory_pos: int | None = None,
    captured_pieces: List[int] | None = None,
) -> GameEventResult:
    next_mover = _opponent(mover_color)
    return GameEventResult(
        message_code=message_code,
        message_params=message_params or {},
        movers_color=next_mover,
        updated_positions=positions,
        captured_positions=captured_positions or [],
        game_over=game_over,
        winner_color=winner_color,
        draw_reason=draw_reason,
        opportunity_pass_the_move=opportunity_pass,
        position_for_mandatory_capture=mandatory_pos,
        captured_pieces=captured_pieces or [],
    )


def _opponent(color: str) -> str:
    return "черный" if color == "белый" else "белый"


def has_mandatory_from_position(cells: dict, color: str, pos: int = None) -> bool:
    board = Board(cells)
    mandatory = get_all_mandatory_captures(board, color)
    if pos is not None:
        return any(f == pos for f, _ in mandatory)
    return len(mandatory) > 0
