"""Сборка WS-ответов и обновление состояния игры после хода."""

import hashlib

from game_engine.models import GameEvent
from backend.state import get_room, set_room, set_game
from backend.board_utils import keys_int_to_str, keys_str_to_int, change_position_name_from_frontend


def opposite_color(color: str) -> str:
    return "черный" if color == "белый" else "белый"


def resolve_creator_color(preference: str, room_id: str) -> str:
    """Цвет создателя комнаты: фиксированный или псевдослучайный по room_id."""
    if preference == "белый":
        return "белый"
    if preference == "черный":
        return "черный"
    h = int(hashlib.md5(room_id.encode()).hexdigest(), 16)
    return "белый" if h % 2 == 0 else "черный"


def assign_player_color(room_data: dict, client_id: str, players: dict) -> str:
    """Назначает цвет новому игроку с учётом предпочтения создателя."""
    creator_id = room_data.get("creator_client_id")
    pref = room_data.get("creator_color_preference", "random")
    room_id = room_data["room_id"]
    creator_col = resolve_creator_color(pref, room_id)

    if client_id == creator_id:
        for oid in players:
            if oid != client_id:
                players[oid] = opposite_color(creator_col)
        return creator_col

    if creator_id and creator_id in players:
        return opposite_color(players[creator_id])

    return opposite_color(creator_col)


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
        "move_history": game.get("move_history", []),
        # If the game already ended (e.g. resign) and client reloads, ensure
        # frontend sees terminal state and doesn't allow continuing.
        "game_over": bool(game.get("game_over", False)),
        "winner": game.get("winner") or "",
        "reason": game.get("reason") or "",
        "draw_offer_from": game.get("draw_offer_from"),
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
    # Defensive: filter out any non-real history entries and renumber sequentially.
    filtered_history = []
    last_desk = None
    for entry in game.get("move_history", []) or []:
        desk = entry.get("desk")
        if not entry.get("from_pos") or not entry.get("to_pos") or not desk:
            continue
        if last_desk is not None and desk == last_desk:
            continue
        filtered_history.append({**entry})
        last_desk = desk
    for i, e in enumerate(filtered_history, start=1):
        e["move_number"] = i

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
        "move_history": filtered_history,
    }
    if result.movers_color and result.movers_color != prev_mover:
        response["position_for_mandatory_capture"] = None
    return response


def update_captures(game: dict, result) -> None:
    if result.movers_color and result.movers_color != game.get("mover"):
        game["pending_batyr_captures"] = []
    elif result.captured_pieces:
        game["pending_batyr_captures"] = result.captured_pieces
    elif not result.position_for_mandatory_capture:
        game["pending_batyr_captures"] = []


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
    def _norm_board(b: dict) -> dict:
        # normalize key types (int/str) to avoid false "changed" comparisons
        out = {}
        for k, v in (b or {}).items():
            try:
                out[int(k)] = v
            except Exception:
                out[k] = v
        return out

    prev_board = _norm_board(game.get("board", {}))
    if result.updated_positions:
        game["board"] = result.updated_positions

    if result.movers_color and result.movers_color != prev_mover:
        game["moves_made"] = game.get("moves_made", 0) + 1
        await apply_increment(room_id, prev_mover)

    update_captures(game, result)

    if result.movers_color:
        game["mover"] = result.movers_color

    if result.game_over:
        game["game_over"] = True
        if result.winner:
            game["winner"] = result.winner
        room_data = await get_room(room_id)
        if room_data and room_data.get("type") != "ai":
            room_data["rematch_ready"] = []
            await set_room(room_id, room_data)

    # Пишем в историю только реальные ходы, которые изменили позиции.
    if (
        from_cell is not None
        and to_cell is not None
        and result.updated_positions
        and _norm_board(result.updated_positions) != prev_board
    ):
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


def get_ai_color(room_data: dict) -> str:
    """Цвет бота в AI-комнате (противоположен цвету человека)."""
    players = room_data.get("players") or {}
    if not players:
        return "черный"
    human_color = next(iter(players.values()))
    return opposite_color(human_color)
