import asyncio
import logging
from fastapi import WebSocket
from backend.state import (get_game, set_game, delete_game,
                            get_room, set_room, delete_room,
                            game_timers, disconnect_timers, drop_room_lock,
                            remove_waiting_public_room)
from backend.config import settings
from backend.board_utils import get_starting_board
from backend.db.models import User
from backend.game_archive import mark_game_started
from backend.game_state import GameState
from backend.player_identity import build_players_info, merge_player_meta, user_id_from_meta
from backend.presence import end_session, start_session
from backend.observability.logging import log_extra
from backend.observability.metrics import (
    record_game_started,
    record_ws_connect,
    record_ws_disconnect,
    record_ws_reject,
)

logger = logging.getLogger(__name__)

_EMPTY_ROOM_GRACE_SECONDS = settings.empty_room_grace_seconds


async def _close_ws_quietly(ws: WebSocket, *, code: int = 1000, reason: str = "") -> None:
    try:
        await ws.close(code=code, reason=reason)
    except Exception:
        pass


async def _delete_room_after_grace(room_id: str, delay_seconds: float):
    """
    Удаляет комнату/игру после небольшой задержки, если за это время никто не переподключился.
    Нужна для предотвращения ложных удалений при быстрых реконнектах (например, dev StrictMode).
    """
    try:
        await asyncio.sleep(delay_seconds)
        # Если кто-то уже переподключился — не трогаем.
        if manager.connections.get(room_id):
            return
        room_data = await get_room(room_id)
        if not room_data:
            return
        game = await get_game(room_id)
        if room_data.get("game_started") and not (game and game.get("game_over")):
            return
        await delete_game(room_id)
        await delete_room(room_id)
        drop_room_lock(room_id)
        logger.info("Room %s deleted after grace timeout", room_id)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning("Failed to delete room %s after grace: %s", room_id, e)


class ConnectionManager:
    def __init__(self):
        # room_id -> {client_id: WebSocket}
        self.connections: dict[str, dict[str, WebSocket]] = {}
        # room_id -> {client_id: proto_version}
        self._proto: dict[str, dict[str, int]] = {}

    def connected_client_ids(self) -> frozenset[str]:
        """client_id с активным WebSocket (для live online, без orphan presence в БД)."""
        ids: set[str] = set()
        for room_conns in self.connections.values():
            ids.update(room_conns.keys())
        return frozenset(ids)

    async def connect(
        self,
        room_id: str,
        websocket: WebSocket,
        client_id: str,
        user: User | None = None,
        *,
        proto: int = 1,
    ) -> bool:
        await websocket.accept()
        room_data = await get_room(room_id)
        if not room_data:
            await websocket.close(code=1008, reason="room_not_found")
            record_ws_reject("room_not_found")
            logger.warning(
                "WS rejected: room_not_found",
                extra=log_extra(room_id=room_id, client_id=client_id[:8]),
            )
            return False

        if room_id not in self.connections:
            self.connections[room_id] = {}

        players = room_data.setdefault("players", {})
        player_meta = room_data.setdefault("player_meta", {})
        meta = merge_player_meta(player_meta.get(client_id), user)
        player_meta[client_id] = meta
        if client_id == room_data.get("creator_client_id") and not meta.get("is_anonymous", True):
            username = meta.get("username")
            if username:
                room_data["creator_username"] = username

        async def _record_presence() -> None:
            await start_session(
                client_id=client_id,
                user_id=user_id_from_meta(meta) or (user.id if user else None),
                is_anonymous=bool(meta.get("is_anonymous", True)),
                room_id=room_id,
            )

        # Reconnect: client_id уже в комнате
        if client_id in players:
            existing_ws = self.connections.get(room_id, {}).get(client_id)
            if existing_ws is not None and existing_ws is not websocket:
                await _close_ws_quietly(existing_ws, code=1000, reason="replaced_by_reconnect")
                self.connections[room_id][client_id] = websocket
                self._proto.setdefault(room_id, {})[client_id] = proto
                task = disconnect_timers.pop(room_id, None)
                if task and not task.done():
                    task.cancel()
                opponent = self.get_opponent_ws(room_id, client_id)
                if opponent:
                    try:
                        await opponent.send_json({"status": "opponent_reconnected"})
                    except Exception:
                        pass
                await set_room(room_id, room_data)
                await _record_presence()
                record_ws_connect(reason="reconnect_replace")
                return True

            if client_id in self.connections.get(room_id, {}):
                await websocket.close(code=1008, reason="already_in_game")
                record_ws_reject("already_in_game")
                logger.warning(
                    "WS rejected: already_in_game",
                    extra=log_extra(room_id=room_id, client_id=client_id[:8]),
                )
                return False
            self.connections[room_id][client_id] = websocket
            self._proto.setdefault(room_id, {})[client_id] = proto

            # Отменяем таймер отключения
            task = disconnect_timers.pop(room_id, None)
            if task and not task.done():
                task.cancel()
            # Уведомляем соперника
            opponent = self.get_opponent_ws(room_id, client_id)
            if opponent:
                try:
                    await opponent.send_json({"status": "opponent_reconnected"})
                except Exception:
                    pass
            await set_room(room_id, room_data)
            await _record_presence()
            record_ws_connect(reason="reconnect")
            return True

        # Новый игрок
        if len(players) >= 2:
            # Комната заполнена
            await websocket.close(code=1008, reason="room_full")
            record_ws_reject("room_full")
            logger.warning(
                "WS rejected: room_full",
                extra=log_extra(room_id=room_id, client_id=client_id[:8]),
            )
            return False

        from backend.game_helpers import assign_player_color

        players[client_id] = assign_player_color(room_data, client_id, players)

        self.connections[room_id][client_id] = websocket
        self._proto.setdefault(room_id, {})[client_id] = proto
        await set_room(room_id, room_data)
        await _record_presence()
        record_ws_connect()
        logger.info(
            "Player %s joined room %s as %s",
            client_id[:6],
            room_id,
            players[client_id],
            extra=log_extra(room_id=room_id, client_id=client_id[:8], color=players[client_id]),
        )
        return True

    async def _destroy_room(self, room_id: str, open_connections: dict[str, WebSocket] | None = None):
        """Удаляет комнату, игру и закрывает все активные WebSocket-соединения."""
        conns = open_connections if open_connections is not None else self.connections.get(room_id, {})
        for ws in list(conns.values()):
            try:
                await ws.close(code=1000, reason="room_closed")
            except Exception:
                pass
        self.connections.pop(room_id, None)
        self._proto.pop(room_id, None)

        task = disconnect_timers.pop(room_id, None)
        if task and not task.done():
            task.cancel()
        from backend.timers import stop_game_timer
        stop_game_timer(room_id)

        await delete_game(room_id)
        await delete_room(room_id)
        drop_room_lock(room_id)
        logger.info("Room %s deleted", room_id)

    async def disconnect(self, room_id: str, websocket: WebSocket):
        room_conns = self.connections.get(room_id, {})
        client_id = None
        for cid, ws in list(room_conns.items()):
            if ws == websocket:
                client_id = cid
                room_conns.pop(cid, None)
                break

        if client_id:
            await end_session(client_id)
            record_ws_disconnect()
            self._proto.get(room_id, {}).pop(client_id, None)

        room_data = await get_room(room_id)
        # Не удаляем комнату мгновенно, если отключился creator:
        # при быстрых реконнектах (и в dev StrictMode) это приводит к "Комната не найдена".

        if not room_conns:
            self.connections.pop(room_id, None)
            self._proto.pop(room_id, None)
            if room_data and room_data.get("type") != "ai":
                # Даём небольшой grace-период на переподключение.
                task = disconnect_timers.pop(room_id, None)
                if task and not task.done():
                    task.cancel()
                disconnect_timers[room_id] = asyncio.create_task(
                    _delete_room_after_grace(room_id, _EMPTY_ROOM_GRACE_SECONDS)
                )
                logger.info("Room %s scheduled for deletion (no players left)", room_id)
            elif room_data and room_data.get("type") == "ai":
                logger.info("AI room %s: no connections left, keeping data", room_id)
        elif room_data:
            await set_room(room_id, room_data)

    def get_client_id(self, room_id: str, websocket: WebSocket) -> str | None:
        for cid, ws in self.connections.get(room_id, {}).items():
            if ws == websocket:
                return cid
        return None

    def get_ws(self, room_id: str, client_id: str) -> WebSocket | None:
        return self.connections.get(room_id, {}).get(client_id)

    def get_opponent_ws(self, room_id: str, client_id: str) -> WebSocket | None:
        for cid, ws in self.connections.get(room_id, {}).items():
            if cid != client_id:
                return ws
        return None

    def connection_proto(self, room_id: str, client_id: str) -> int:
        return self._proto.get(room_id, {}).get(client_id, 1)

    async def send_to_room(self, room_id: str, data: dict, *, proto: int | None = None):
        room_conns = self.connections.get(room_id, {})
        room_proto = self._proto.get(room_id, {})
        for client_id, ws in room_conns.items():
            if proto is not None and room_proto.get(client_id, 1) != proto:
                continue
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning("send_to_room(%s): %s", room_id, e)

    async def broadcast_move(
        self,
        room_id: str,
        game: dict,
        result,
        prev_mover: str,
        from_cell: int | None,
        to_cell: int | None,
        *,
        board_before: dict | None = None,
    ) -> None:
        from backend.session.v2.protocol import build_move_delta
        from backend.state import get_room

        room_data = await get_room(room_id)
        payload = build_move_delta(
            game, result, prev_mover, from_cell, to_cell, room_data,
            board_before=board_before,
        )
        await self.send_to_room(room_id, payload)

    async def send_join_state(
        self,
        websocket: WebSocket,
        room_id: str,
        client_id: str,
        game: dict,
        room_data: dict,
        my_color: str,
    ) -> None:
        from backend.session.v2.protocol import build_snapshot

        await self.send_to_player(
            websocket,
            build_snapshot(
                game,
                room_data,
                my_color,
                players_info=build_players_info(room_data),
            ),
        )

    async def send_to_player(self, websocket: WebSocket, data: dict):
        try:
            await websocket.send_json(data)
        except Exception as e:
            logger.warning("send_to_player: %s", e)


manager = ConnectionManager()


async def init_game(room_id: str):
    """Создаёт начальное состояние игры в Redis."""
    game = GameState.new(get_starting_board())
    await set_game(room_id, game.to_storage())


async def handle_player2_join(room_id: str, room_data: dict):
    await init_game(room_id)
    game = await get_game(room_id)

    if room_data.get("type") in ("public", "private"):
        from backend.player_identity import refresh_pvp_ratings_for_room

        await refresh_pvp_ratings_for_room(room_data)

    for cid, color in room_data.get("players", {}).items():
        ws = manager.get_ws(room_id, cid)
        if ws:
            await manager.send_join_state(ws, room_id, cid, game, room_data, color)

    room_data["game_started"] = True
    mark_game_started(room_data)
    await remove_waiting_public_room(room_id)
    await set_room(room_id, room_data)
    record_game_started(room_data.get("type") or "unknown")
    logger.info(
        "Game started in room %s (type=%s)",
        room_id,
        room_data.get("type"),
        extra=log_extra(room_id=room_id, room_type=room_data.get("type")),
    )

    if room_data.get("time_control"):
        from backend.timers import stop_game_timer, game_ticker as gt
        stop_game_timer(room_id)
        game_timers[room_id] = asyncio.create_task(gt(room_id))