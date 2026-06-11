"""Сборка WS-ответов и обновление состояния игры после хода."""

import hashlib
import time

from game_engine.models import GameEvent
from backend.player_identity import build_players_info
from backend.state import get_room, set_room, set_game
from backend.board_utils import keys_int_to_str, keys_str_to_int, change_position_name_from_frontend


def opposite_color(color: str) -> str:
    return "черный" if color == "белый" else "белый"


def _resolve_game_end_reason(result) -> str | None:
    """Map engine end state to a stable reason code for archive and metrics."""
    if result.draw_reason:
        return result.draw_reason
    if result.game_over and result.winner_color:
        return "biy_wins"
    return None


def color_has_moved(game: dict | None, color: str) -> bool:
    """True, если сторона уже сделала хотя бы один записанный ход."""
    if not game or not color:
        return False
    return any(e.get("mover") == color for e in (game.get("move_history") or []))


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


def compute_clock_times(
    room_data: dict,
    game: dict | None,
    *,
    now: float | None = None,
) -> dict[str, float] | None:
    """Display clock times from stored values + elapsed since last_tick (read-only)."""
    if not room_data.get("time_control"):
        return None
    white = room_data.get("timer_white")
    black = room_data.get("timer_black")
    if white is None or black is None:
        return None

    now = now if now is not None else time.time()
    last_tick = room_data.get("last_tick")
    elapsed = (now - last_tick) if last_tick is not None else 0.0
    mover = game.get("mover") if game else None

    if mover == "белый" and game and color_has_moved(game, "белый"):
        white = max(0.0, float(white) - elapsed)
    elif mover == "черный" and game and color_has_moved(game, "черный"):
        black = max(0.0, float(black) - elapsed)

    return {"белый": white, "черный": black}


def _timer_fields(room_data: dict, game: dict | None = None) -> dict:
    if not room_data.get("time_control"):
        return {}
    times = compute_clock_times(room_data, game) or {
        "белый": room_data.get("timer_white") or 0,
        "черный": room_data.get("timer_black") or 0,
    }
    return {
        "time_control": room_data["time_control"],
        "increment": room_data.get("increment"),
        "time": times,
    }


def build_game_started_response(game: dict, room_data: dict, my_color: str) -> dict:
    response = {
        "status": "game_started",
        "movers_color": game["mover"],
        "desk": keys_int_to_str(game["board"]),
        "your_color": my_color,
        "players_info": build_players_info(room_data),
        "move_history": game.get("move_history", []),
        # If the game already ended (e.g. resign) and client reloads, ensure
        # frontend sees terminal state and doesn't allow continuing.
        "game_over": bool(game.get("game_over", False)),
        "winner_color": game.get("winner_color") or game.get("winner") or "",
        "reason": game.get("reason") or "",
        "draw_offer_from": game.get("draw_offer_from"),
        **_timer_fields(room_data, game),
    }
    return response


def build_move_response(
    game: dict,
    result,
    prev_mover: str,
    move_from: int | None = None,
    move_to: int | None = None,
    hint_position: int | None = None,
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
        "message_code": result.message_code or None,
        "movers_color": result.movers_color,
        "desk": keys_int_to_str(game["board"]),
        "game_over": result.game_over,
        "winner_color": result.winner_color,
        "position_for_mandatory_capture": result.position_for_mandatory_capture,
        "opportunity_pass_the_move": result.opportunity_pass_the_move,
        "essential_positions": result.essential_positions,
        "captured_pieces": result.captured_pieces,
        "captured_positions": result.captured_positions,
        "from_pos": move_from,
        "to_pos": move_to,
        "move_history": filtered_history,
    }
    if result.message_params:
        response["message_params"] = result.message_params
    end_reason = _resolve_game_end_reason(result)
    if end_reason:
        response["reason"] = end_reason
    response = {k: v for k, v in response.items() if v is not None}
    if result.movers_color and result.movers_color != prev_mover:
        response["position_for_mandatory_capture"] = None
    if hint_position is not None:
        response["hint_position"] = hint_position
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


async def apply_increment(room_data: dict, prev_mover: str) -> None:
    if not room_data.get("increment") or not room_data.get("time_control"):
        return
    inc = float(room_data["increment"])
    if prev_mover == "белый" and room_data.get("timer_white") is not None:
        room_data["timer_white"] += inc
    elif prev_mover == "черный" and room_data.get("timer_black") is not None:
        room_data["timer_black"] += inc


async def finalize_clock_on_move(
    room_id: str,
    game: dict,
    prev_mover: str,
    *,
    turn_passed: bool,
) -> None:
    """Fix stored clocks on turn pass: deduct elapsed, add increment, reset last_tick."""
    if not turn_passed:
        return

    room_data = await get_room(room_id)
    if not room_data or not room_data.get("time_control"):
        return

    now = time.time()
    last_tick = room_data.get("last_tick")
    if last_tick is not None and color_has_moved(game, prev_mover):
        elapsed = now - last_tick
        if prev_mover == "белый" and room_data.get("timer_white") is not None:
            room_data["timer_white"] = max(0.0, room_data["timer_white"] - elapsed)
        elif prev_mover == "черный" and room_data.get("timer_black") is not None:
            room_data["timer_black"] = max(0.0, room_data["timer_black"] - elapsed)

    await apply_increment(room_data, prev_mover)
    room_data["last_tick"] = now
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
    prev_board = _norm_board_keys(game.get("board", {}))
    if result.updated_positions:
        game["board"] = result.updated_positions

    turn_passed = bool(result.movers_color and result.movers_color != prev_mover)
    await finalize_clock_on_move(room_id, game, prev_mover, turn_passed=turn_passed)

    if turn_passed:
        game["moves_made"] = game.get("moves_made", 0) + 1

    update_captures(game, result)

    if result.movers_color:
        game["mover"] = result.movers_color

    if result.game_over:
        game["game_over"] = True
        if result.winner_color:
            game["winner_color"] = result.winner_color
            game["winner"] = result.winner_color
        end_reason = _resolve_game_end_reason(result)
        if end_reason:
            game["reason"] = end_reason
        room_data = await get_room(room_id)
        if room_data and room_data.get("type") != "ai":
            room_data["rematch_ready"] = []
            await set_room(room_id, room_data)

    # Пишем в историю только реальные ходы, которые изменили позиции.
    if (
        from_cell is not None
        and to_cell is not None
        and result.updated_positions
        and _norm_board_keys(result.updated_positions) != prev_board
    ):
        save_move_to_history(
            game,
            prev_mover,
            from_cell,
            to_cell,
            captured_positions=result.captured_positions,
        )

    await set_game(room_id, game)
    response = build_move_response(game, result, prev_mover, from_cell, to_cell)
    room_data = await get_room(room_id)
    if room_data:
        response.update(_timer_fields(room_data, game))
    if result.game_over:
        from backend.game_finish import complete_game_after_move

        await complete_game_after_move(room_id)
    return response


def ws_error_payload(code: str, **params) -> dict:
    from backend.message_codes import ws_error
    return ws_error(code, **params)


def is_hint_ws_message(data: dict) -> bool:
    """Hint request: position only, no move_from/move_to. Board not required."""
    if not isinstance(data, dict):
        return False
    if data.get("move_from") or data.get("move_to"):
        return False
    return bool(data.get("position"))


def parse_hint_request(data: dict) -> int:
    raw = data.get("position")
    if raw is None:
        raise ValueError("ws.invalid_move_data")
    try:
        return change_position_name_from_frontend(raw)
    except (TypeError, ValueError):
        raise ValueError("ws.invalid_move_data") from None


def build_hint_event_from_game(game: dict, hint_cell: int) -> GameEvent:
    return GameEvent(
        positions=_norm_board_keys(game.get("board", {})),
        mover_color=game["mover"],
        position=hint_cell,
        position_for_mandatory_capture=game.get("pending_mandatory_position"),
    )


def is_move_message(data: dict) -> bool:
    return isinstance(data, dict) and isinstance(data.get("board"), dict) and "movers_color" in data


def _norm_board_keys(board: dict) -> dict:
    out = {}
    for k, v in (board or {}).items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            out[k] = v
    return out


def is_hint_request(raw_from: int | None, raw_to: int | None, event) -> bool:
    """Запрос подсказок: выбрана клетка (position), ход from/to не указан."""
    return raw_from is None and raw_to is None and event.position is not None


def is_rejected_move(
    result,
    prev_board: dict,
    raw_from: int | None,
    raw_to: int | None,
) -> bool:
    """Ход отклонён движком: есть сообщение об ошибке, доска не изменилась."""
    if raw_from is None or raw_to is None:
        return False
    if raw_from == 0 and raw_to == 0:
        return False
    if result.game_over or result.essential_positions:
        return False
    if not result.message_code:
        return False
    new_board = _norm_board_keys(result.updated_positions) if result.updated_positions else prev_board
    return new_board == _norm_board_keys(prev_board)


def parse_client_event(data: dict) -> tuple[GameEvent, int | None, int | None]:
    if not isinstance(data.get("board"), dict):
        raise ValueError("ws.missing_board")
    if not data.get("movers_color"):
        raise ValueError("ws.missing_mover")

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
