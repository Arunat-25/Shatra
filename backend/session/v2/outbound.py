"""Proto-aware outbound messages for v2 WebSocket clients."""

from __future__ import annotations

from fastapi import WebSocket

from backend.session.v2.protocol import PROTO_VERSION, wrap_control_v1
from backend.ws_manager import manager


async def send_control_v1(room_id: str, client_id: str, ws: WebSocket, payload: dict) -> None:
    """Send legacy `{status: ...}` control payload, wrapped for v2 clients when needed."""
    if not payload:
        return
    proto = manager.connection_proto(room_id, client_id)
    out = payload
    if payload.get("status") and proto >= PROTO_VERSION:
        out = wrap_control_v1({**payload, "type": payload["status"]})
    await manager.send_to_player(ws, out)


async def broadcast_control_v1(room_id: str, build_payload) -> None:
    """Broadcast per-client control payloads built by `build_payload(client_id)`."""
    for cid, ws in list(manager.connections.get(room_id, {}).items()):
        payload = build_payload(cid)
        if payload is not None:
            await send_control_v1(room_id, cid, ws, payload)
