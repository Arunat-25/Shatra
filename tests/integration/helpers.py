"""Helpers for REST → WebSocket → archive integration tests."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any, Callable

import redis

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "1"))


def new_client_id() -> str:
    return uuid.uuid4().hex


def ws_path(room_id: str, client_id: str, access_token: str | None = None) -> str:
    path = f"/ws/v2/{room_id}/?client_id={client_id}"
    if access_token:
        path += f"&access_token={access_token}"
    return path


def redis_client() -> redis.Redis:
    return redis.Redis(
        host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True
    )


def flush_redis() -> None:
    redis_client().flushdb()


def read_room_json(room_id: str) -> dict | None:
    raw = redis_client().get(f"room:{room_id}")
    if not raw:
        return None
    return json.loads(raw)


def _is_v2_message(msg: dict) -> bool:
    return isinstance(msg, dict) and msg.get("v") == 2 and isinstance(msg.get("t"), str)


def _skip_ws_noise(msg: dict) -> bool:
    if msg.get("type") in {"timer_tick", "disconnect_tick"}:
        return True
    if _is_v2_message(msg) and msg.get("t") == "clock":
        return True
    return False


def _is_game_started(msg: dict) -> bool:
    if msg.get("status") == "game_started":
        return True
    return (
        _is_v2_message(msg)
        and msg.get("t") == "snapshot"
        and msg.get("board") is not None
        and not msg.get("gameOver")
    )


def _is_game_over(msg: dict) -> bool:
    if msg.get("game_over") is True:
        return True
    if not _is_v2_message(msg):
        return False
    if msg.get("t") == "gameOver":
        return True
    if msg.get("t") in {"snapshot", "move"} and msg.get("gameOver"):
        return True
    return False


def _is_waiting(msg: dict) -> bool:
    if msg.get("status") == "waiting":
        return True
    return _is_v2_message(msg) and msg.get("t") == "waiting"


def receive_until(
    ws,
    predicate: Callable[[dict], bool],
    *,
    max_messages: int = 120,
) -> dict:
    for _ in range(max_messages):
        msg = ws.receive_json()
        if _skip_ws_noise(msg):
            continue
        if predicate(msg):
            return msg
    raise AssertionError("expected WebSocket message not received")


def wait_game_started(ws) -> dict:
    return receive_until(ws, _is_game_started)


def wait_chat(ws, *, text: str | None = None) -> dict:
    return receive_until(
        ws,
        lambda m: m.get("type") == "chat"
        and (text is None or m.get("text") == text),
    )


def wait_chat_history(ws) -> dict:
    return receive_until(ws, lambda m: m.get("type") == "chat_history")


def wait_error_code(ws, code: str) -> dict:
    skip_types = {"timer_tick", "disconnect_tick"}
    for _ in range(120):
        msg = ws.receive_json()
        if msg.get("type") in skip_types:
            continue
        if msg.get("status") == "error" and msg.get("message_code") == code:
            return msg
    raise AssertionError(f"expected error {code!r} not received")


def wait_waiting(ws) -> dict:
    return receive_until(ws, _is_waiting)


def resign_and_finish(ws) -> dict:
    ws.send_json({"v": 2, "t": "resign"})
    return receive_until(ws, _is_game_over)


def ensure_game_archived(client, room_id: str, db_scalar_fn=None):
    """TestClient: archive в WS-handler может зависнуть — дожимаем через portal."""
    import json
    import time

    from backend.game_archive import archive_finished_game

    if db_scalar_fn is not None:
        for _ in range(40):
            if db_scalar_fn(
                "SELECT COUNT(*) FROM finished_games WHERE room_id = %s", (room_id,)
            ) >= 1:
                return None
            time.sleep(0.05)

    raw = redis_client().get(f"game:{room_id}")
    if not raw:
        return None
    game = json.loads(raw)
    if game.get("archived"):
        return None
    if not game.get("game_over"):
        return None
    return client.portal.call(archive_finished_game, room_id)


def finish_game(client, ws, room_id: str, db_scalar_fn=None) -> dict:
    msg = resign_and_finish(ws)
    ensure_game_archived(client, room_id, db_scalar_fn=db_scalar_fn)
    return msg


def create_room(
    client,
    *,
    room_type: str = "ai",
    client_id: str | None = None,
    headers: dict | None = None,
    **extra,
) -> str:
    payload: dict[str, Any] = {"type": room_type, **extra}
    if client_id is not None:
        payload["creator_client_id"] = client_id
    r = client.post("/rooms", json=payload, headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()["room_id"]


def auth_headers(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def assert_finished_game_row(
    db_fetchone,
    room_id: str,
    *,
    room_type: str | None = None,
    white_user_id: str | None = ...,  # type: ignore[assignment]
    black_user_id: str | None = ...,  # type: ignore[assignment]
    white_is_anonymous: bool | None = None,
    black_is_anonymous: bool | None = None,
) -> tuple:
    row = db_fetchone(
        """
        SELECT room_type, white_user_id, black_user_id,
               white_is_anonymous, black_is_anonymous, reason
        FROM finished_games WHERE room_id = %s
        """,
        (room_id,),
    )
    assert row is not None, f"finished_games row missing for room {room_id}"
    if room_type is not None:
        assert row[0] == room_type
    if white_user_id is not ...:
        expected = str(white_user_id) if white_user_id is not None else None
        actual = str(row[1]) if row[1] is not None else None
        assert actual == expected, f"white_user_id: {actual!r} != {expected!r}"
    if black_user_id is not ...:
        expected = str(black_user_id) if black_user_id is not None else None
        actual = str(row[2]) if row[2] is not None else None
        assert actual == expected, f"black_user_id: {actual!r} != {expected!r}"
    if white_is_anonymous is not None:
        assert row[3] is white_is_anonymous
    if black_is_anonymous is not None:
        assert row[4] is black_is_anonymous
    return row


def assert_finished_game_for_player(
    db_fetchone,
    room_id: str,
    client_id: str,
    *,
    user_id: str | None = ...,
    is_anonymous: bool | None = None,
    room_data: dict | None = None,
) -> tuple:
    """Assert finished_games row for the color assigned to client_id."""
    room = room_data or read_room_json(room_id)
    assert room is not None, f"room {room_id} missing in Redis"
    color = room["players"][client_id]
    row = db_fetchone(
        """
        SELECT room_type, white_user_id, black_user_id,
               white_is_anonymous, black_is_anonymous, reason
        FROM finished_games WHERE room_id = %s
        """,
        (room_id,),
    )
    assert row is not None, f"finished_games row missing for room {room_id}"
    if color == "белый":
        uid_col, anon_col = row[1], row[3]
    else:
        uid_col, anon_col = row[2], row[4]
    if user_id is not ...:
        expected = str(user_id) if user_id is not None else None
        actual = str(uid_col) if uid_col is not None else None
        assert actual == expected, f"user_id for {client_id} ({color}): {actual!r} != {expected!r}"
    if is_anonymous is not None:
        assert anon_col is is_anonymous
    return row
