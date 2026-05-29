import asyncio
import logging
from fastapi import WebSocket
from backend.state import (get_game, set_game, delete_game,
                            get_room, set_room, delete_room,
                            game_timers, disconnect_timers, drop_room_lock)
from backend.config import settings
from backend.board_utils import get_starting_board
from backend.db.models import User
from backend.game_helpers import build_game_started_response
from backend.game_state import GameState
from backend.player_identity import meta_from_user

logger = logging.getLogger(__name__)

_EMPTY_ROOM_GRACE_SECONDS = settings.empty_room_grace_seconds


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
        # Если игра уже началась — эту ветку не используем.
        if room_data.get("game_started"):
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

    async def connect(
        self,
        room_id: str,
        websocket: WebSocket,
        client_id: str,
        user: User | None = None,
    ) -> bool:
        await websocket.accept()
        room_data = await get_room(room_id)
        if not room_data:
            await websocket.close(code=1008, reason="Комната не найдена")
            return False

        if room_id not in self.connections:
            self.connections[room_id] = {}

        players = room_data.setdefault("players", {})
        player_meta = room_data.setdefault("player_meta", {})
        player_meta[client_id] = meta_from_user(user)

        # Reconnect: client_id уже в комнате — только если нет активного WS
        if client_id in players:
            if client_id in self.connections.get(room_id, {}):
                # Уже есть активное соединение — это не reconnect, а дубль
                await websocket.close(code=1008, reason="Вы уже в игре")
                return False
            self.connections[room_id][client_id] = websocket

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
            return True

        # Новый игрок
        if len(players) >= 2:
            # Комната заполнена
            await websocket.close(code=1008, reason="Комната уже заполнена")
            return False

        from backend.game_helpers import assign_player_color

        players[client_id] = assign_player_color(room_data, client_id, players)

        self.connections[room_id][client_id] = websocket
        await set_room(room_id, room_data)
        logger.info("Player %s joined room %s as %s", client_id[:6], room_id, players[client_id])
        return True

    async def _destroy_room(self, room_id: str, open_connections: dict[str, WebSocket] | None = None):
        """Удаляет комнату, игру и закрывает все активные WebSocket-соединения."""
        conns = open_connections if open_connections is not None else self.connections.get(room_id, {})
        for ws in list(conns.values()):
            try:
                await ws.close(code=1000, reason="Комната закрыта")
            except Exception:
                pass
        self.connections.pop(room_id, None)

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

        room_data = await get_room(room_id)
        # Не удаляем комнату мгновенно, если отключился creator:
        # при быстрых реконнектах (и в dev StrictMode) это приводит к "Комната не найдена".

        if not room_conns:
            self.connections.pop(room_id, None)
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

    async def send_to_room(self, room_id: str, data: dict):
        for ws in self.connections.get(room_id, {}).values():
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning("send_to_room(%s): %s", room_id, e)

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

    for cid, color in room_data.get("players", {}).items():
        response = build_game_started_response(game, room_data, color)
        ws = manager.get_ws(room_id, cid)
        if ws:
            await manager.send_to_player(ws, response)

    room_data["game_started"] = True
    await set_room(room_id, room_data)

    if room_data.get("time_control"):
        from backend.timers import stop_game_timer, game_ticker as gt
        stop_game_timer(room_id)
        game_timers[room_id] = asyncio.create_task(gt(room_id))