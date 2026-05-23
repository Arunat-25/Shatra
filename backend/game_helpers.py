"""Сборка WS-ответов и обновление состояния игры после хода."""

from game_engine.models import GameEvent
from backend.state import get_room, set_room, set_game
from backend.board_utils import keys_int_to_str, keys_str_to_int, change_position_name_from_frontend


def _timer_fields(room_data: dict) -> dict:
    if not room_data.get("time_control"):
        return {}
    return {
        "time_control": room_data["time_control"],
        "increment": room_data.get("increment"),
        "time": {
            "белый": room_data.get("timer_white") or 0,
            "черный": room_data.get("timer_black") or 0,
        },
    }


def build_game_started_response(game: dict, room_data: dict, my_color: str) -> dict:
    response = {
        "status": "game_started",
        "movers_color": game["mover"],
        "desk": keys_int_to_str(game["board"]),
        "your_color": my_color,
        **_timer_fields(room_data),
    }
    return response


def build_move_response(
    game: dict,
    result,
    prev_mover: str,
    move_from: int | None = None,
    move_to: int | None = None,
) -> dict:
    response = {
        "message": result.message,
        "movers_color": result.movers_color,
        "desk": keys_int_to_str(game["board"]),
        "game_over": result.game_over,
        "winner": result.winner,
        "position_for_mandatory_capture": result.position_for_mandatory_capture,
        "opportunity_pass_the_move": result.opportunity_pass_the_move,
        "essential_positions": result.essential_positions,
        "captured_pieces": result.captured_pieces,
        "captured_positions": result.captured_positions,
        "from_pos": move_from,
        "to_pos": move_to,
        "move_history": game.get("move_history", []),
    }
    if result.movers_color and result.movers_color != prev_mover:
        response["position_for_mandatory_capture"] = None
    return response


def update_captures(game: dict, result) -> None:
    if result.movers_color and result.movers_color != game.get("mover"):
        game["pending_batyr_captures"] = []
    elif result.captured_pieces:
        game["pending_batyr_captures"] = result.captured_pieces


def save_move_to_history(
    game: dict,
    mover: str,
    from_cell: int,
    to_cell: int,
    captured_positions: list[int] | None = None,
) -> None:
    history = game.setdefault("move_history", [])
    entry = {
        "move_number": len(history) + 1,
        "mover": mover,
        "from_pos": from_cell,
        "to_pos": to_cell,
        "desk": keys_int_to_str(game["board"]),
    }
    if captured_positions:
        entry["captured_positions"] = captured_positions
    history.append(entry)


async def apply_increment(room_id: str, prev_mover: str) -> None:
    room_data = await get_room(room_id)
    if not room_data or not room_data.get("increment") or not room_data.get("time_control"):
        return
    if prev_mover == "белый" and room_data.get("timer_white") is not None:
        room_data["timer_white"] += float(room_data["increment"])
    elif prev_mover == "черный" and room_data.get("timer_black") is not None:
        room_data["timer_black"] += float(room_data["increment"])
    await set_room(room_id, room_data)


async def apply_move_result(
    room_id: str,
    game: dict,
    result,
    prev_mover: str,
    from_cell: int | None = None,
    to_cell: int | None = None,
) -> dict:
    """Применяет результат хода к game в Redis и возвращает WS-ответ."""
    if result.updated_positions:
        game["board"] = result.updated_positions

    if result.movers_color and result.movers_color != prev_mover:
        game["moves_made"] = game.get("moves_made", 0) + 1
        await apply_increment(room_id, prev_mover)

    update_captures(game, result)

    if result.movers_color:
        game["mover"] = result.movers_color

    if from_cell is not None and to_cell is not None:
        save_move_to_history(
            game,
            prev_mover,
            from_cell,
            to_cell,
            captured_positions=result.captured_positions,
        )

    await set_game(room_id, game)
    return build_move_response(game, result, prev_mover, from_cell, to_cell)


def parse_client_event(data: dict) -> tuple[GameEvent, int | None, int | None]:
    raw_from = (
        change_position_name_from_frontend(data.get("move_from"))
        if data.get("move_from")
        else None
    )
    raw_to = (
        change_position_name_from_frontend(data.get("move_to"))
        if data.get("move_to")
        else None
    )
    event = GameEvent(
        positions=keys_str_to_int(data["board"]),
        mover_color=data["movers_color"],
        from_pos=raw_from,
        to_pos=raw_to,
        position=(
            change_position_name_from_frontend(data.get("position"))
            if data.get("position")
            else None
        ),
        position_for_mandatory_capture=data.get("position_for_mandatory_capture"),
    )
    return event, raw_from, raw_to


def get_player_color(room_data: dict, client_id: str) -> str | None:
    return room_data.get("players", {}).get(client_id)
