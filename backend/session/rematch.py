import asyncio
import logging
import time

from backend.game_helpers import build_game_started_response
from backend.game_archive import archive_finished_game, mark_game_started
from backend.message_codes import DRAW_OPPONENT_DECLINED, DRAW_OFFER_CANCELLED, ws_payload
from backend.session.v2.outbound import broadcast_control_v1, send_control_v1
from backend.session.v2.protocol import PROTO_VERSION
from backend.state import get_game, set_game, set_room, game_timers
from backend.timers import stop_game_timer, game_ticker
from backend.ws_manager import manager, init_game

logger = logging.getLogger(__name__)


def _opposite_color(color: str) -> str:
    return "черный" if color == "белый" else "белый"


async def _broadcast_rematch_status(room_id: str, room_data: dict) -> None:
    ready = set(room_data.get("rematch_ready") or [])
    conns = manager.connections.get(room_id, {})

    def build_payload(cid: str) -> dict:
        opp_cid = next((c for c in conns if c != cid), None)
        return {
            "status": "rematch_status",
            "self_ready": cid in ready,
            "opponent_ready": bool(opp_cid and opp_cid in ready),
        }

    await broadcast_control_v1(room_id, build_payload)


async def _start_rematch(room_id: str, room_data: dict) -> None:
    """Сбрасывает игру и запускает реванш для обоих подключённых игроков."""
    stop_game_timer(room_id)

    players = room_data.get("players") or {}
    for cid in list(players.keys()):
        players[cid] = _opposite_color(players[cid])
    room_data["players"] = players

    await archive_finished_game(room_id)
    await init_game(room_id)
    game = await get_game(room_id)
    if not game:
        return

    room_data["rematch_ready"] = []
    if room_data.get("time_control"):
        tc = float(room_data["time_control"])
        room_data["timer_white"] = tc
        room_data["timer_black"] = tc
        room_data["last_tick"] = time.time()
    mark_game_started(room_data)
    await set_room(room_id, room_data)

    for cid, ws in list(manager.connections.get(room_id, {}).items()):
        color = room_data.get("players", {}).get(cid)
        if not ws or not color:
            continue
        if manager.connection_proto(room_id, cid) >= PROTO_VERSION:
            await manager.send_join_state(ws, room_id, cid, game, room_data, color)
        else:
            response = build_game_started_response(game, room_data, color)
            await manager.send_to_player(ws, response)

    if room_data.get("time_control"):
        game_timers[room_id] = asyncio.create_task(game_ticker(room_id))


async def _decline_draw_offer(room_id: str, game: dict, room_data: dict) -> bool:
    """Сбрасывает предложение ничьей и уведомляет игроков. Возвращает True, если было активное предложение."""
    offerer = game.get("draw_offer_from")
    if not offerer:
        return False
    game.pop("draw_offer_from", None)
    await set_game(room_id, game)

    def build_payload(cid: str) -> dict:
        color = room_data.get("players", {}).get(cid)
        code = DRAW_OPPONENT_DECLINED if color == offerer else DRAW_OFFER_CANCELLED
        return {"status": "draw_declined", **ws_payload(code)}

    await broadcast_control_v1(room_id, build_payload)
    return True
