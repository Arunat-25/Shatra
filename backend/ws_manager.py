import asyncio
import logging
from fastapi import WebSocket
from game_engine.game_logic import logic
from backend.state import (redis_client, get_game, set_game, delete_game,
                            get_room, set_room, delete_room,
                            game_timers, disconnect_timers)
from backend.board_utils import keys_int_to_str, get_starting_board

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # room_id -> {player_id: WebSocket}
        self.connections: dict[str, dict[int, WebSocket]] = {}

    async def connect(self, room_id: str, websocket: WebSocket,
                      client_id: str | None = None,
                      player_id: int | None = None) -> bool:
        # Сохраняем переданный player_id отдельно (client_id может его перезаписать)
        player_id_param = player_id
        await websocket.accept()
        room_data = await get_room(room_id)
        if not room_data:
            await websocket.close(code=1008)
            return False

        if room_id not in self.connections:
            self.connections[room_id] = {}

        # Определяем player_id (по приоритету):
        # 1) Переданный player_id из URL (если не занят)
        # 2) По client_id (если привязан и не занят)
        # 3) Назначаем свободный
        if player_id_param is not None and player_id_param not in self.connections[room_id]:
            player_id = player_id_param

        if player_id is None and client_id:
            if (room_data.get("player1_client_id") == client_id
                    and 1 not in self.connections[room_id]):
                player_id = 1
            elif (room_data.get("player2_client_id") == client_id
                    and 2 not in self.connections[room_id]):
                player_id = 2

        if player_id is None:
            # Назначаем свободный
            if 1 not in self.connections[room_id]:
                player_id = 1
            elif 2 not in self.connections[room_id]:
                player_id = 2
            else:
                await websocket.close(code=1008)
                return False

        self.connections[room_id][player_id] = websocket

        if player_id == 1:
            room_data["player1_connected"] = True
            if client_id:
                room_data["player1_client_id"] = client_id
        elif player_id == 2:
            room_data["player2_connected"] = True
            if client_id:
                room_data["player2_client_id"] = client_id
        await set_room(room_id, room_data)

        # Если игра уже началась — проверяем таймер переподключения
        if room_data.get("game_started"):
            task = disconnect_timers.pop(room_id, None)
            if task and not task.done():
                task.cancel()
                other_id = 2 if player_id == 1 else 1
                other_ws = self.get_player_ws(room_id, other_id)
                if other_ws:
                    try:
                        await other_ws.send_json({"status": "opponent_reconnected"})
                    except Exception as e:
                        logger.warning("opponent_reconnected notification failed: %s", e)

        return True

    async def disconnect(self, room_id: str, websocket: WebSocket):
        room_conns = self.connections.get(room_id, {})
        player_id = self._find_player_id(room_id, websocket)
        if player_id:
            room_conns.pop(player_id, None)
            room_data = await get_room(room_id)
            if room_data:
                if player_id == 1:
                    room_data["player1_connected"] = False
                elif player_id == 2:
                    room_data["player2_connected"] = False
                await set_room(room_id, room_data)

        if not room_conns:
            self.connections.pop(room_id, None)

    def _find_player_id(self, room_id: str, websocket: WebSocket) -> int | None:
        for pid, ws in self.connections.get(room_id, {}).items():
            if ws == websocket:
                return pid
        return None

    def get_player_ws(self, room_id: str, player_id: int) -> WebSocket | None:
        return self.connections.get(room_id, {}).get(player_id)

    def get_other_player_ws(self, room_id: str, player_id: int) -> WebSocket | None:
        other = 2 if player_id == 1 else 1
        return self.get_player_ws(room_id, other)

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
    start_board = get_starting_board()
    game_data = {
        "board": start_board,
        "mover": "белый",
        "players": {},
        "pending_batyr_captures": [],
        "moves_made": 0,
        "move_history": [],
    }
    await set_game(room_id, game_data)


async def handle_player2_join(room_id: str, room_data: dict):
    await init_game(room_id)
    game = await get_game(room_id)

    response = {
        "status": "game_started",
        "movers_color": game["mover"],
        "desk": keys_int_to_str(game["board"]),
    }
    if room_data.get("time_control"):
        response["time_control"] = room_data["time_control"]
        response["increment"] = room_data.get("increment")
        response["time"] = {
            "белый": room_data.get("timer_player1") or 0,
            "черный": room_data.get("timer_player2") or 0,
        }

    await manager.send_to_room(room_id, response)

    room_data["game_started"] = True
    await set_room(room_id, room_data)

    if room_data.get("time_control"):
        from backend.timers import game_ticker as gt
        task = asyncio.create_task(gt(room_id))
        game_timers[room_id] = task