"""WS/HTTP message code helpers."""

from __future__ import annotations

from typing import Any

# HTTP / WS close / room
ROOM_NOT_FOUND = "room.not_found"
ROOM_FULL = "room.full"
ROOM_GAME_STARTED = "room.game_started"
ALREADY_IN_GAME = "room.already_in_game"

# Auth
AUTH_REQUIRED = "auth.auth_required"
AUTH_INVALID_TOKEN = "auth.invalid_token"
AUTH_USER_NOT_FOUND = "auth.user_not_found"
AUTH_INVALID_CREDENTIALS = "auth.invalid_credentials"
AUTH_SESSION_EXPIRED = "auth.session_expired"
AUTH_WRONG_PASSWORD = "auth.wrong_password"
AUTH_USERNAME_TAKEN_REGISTER = "auth.username_taken_register"
AUTH_USERNAME_TAKEN_PROFILE = "auth.username_taken_profile"
ADMIN_FORBIDDEN = "admin.forbidden"

# Bug reports
BUG_REPORT_DESCRIPTION_REQUIRED = "bug_report.description_required"
BUG_REPORT_DESCRIPTION_TOO_SHORT = "bug_report.description_too_short"
BUG_REPORT_DESCRIPTION_TOO_LONG = "bug_report.description_too_long"
BUG_REPORT_INVALID_SCREENSHOT = "bug_report.invalid_screenshot"
BUG_REPORT_SCREENSHOT_TOO_LARGE = "bug_report.screenshot_too_large"
BUG_REPORT_NOT_FOUND = "bug_report.not_found"
BUG_REPORT_NO_SCREENSHOT = "bug_report.no_screenshot"

# Draw / rematch / control
DRAW_BOT_DECLINED = "draw.bot_declined"
DRAW_ALREADY_OFFERED = "draw.already_offered"
DRAW_YOU_OFFERED = "draw.you_offered"
DRAW_OPPONENT_OFFERS = "draw.opponent_offers"
DRAW_DECLINED = "draw.declined"
DRAW_AGREED = "draw.agreed"
DRAW_OPPONENT_DECLINED = "draw.opponent_declined"
DRAW_OFFER_CANCELLED = "draw.offer_cancelled"
REMATCH_WAIT_SELF = "rematch.wait_self"
REMATCH_WAIT_OPPONENT = "rematch.wait_opponent"
REMATCH_OPPONENT_LEFT = "rematch.opponent_left"
REMATCH_CANCELLED = "rematch.cancelled"
CANCEL_YOU = "cancel.you"
CANCEL_OPPONENT = "cancel.opponent"
CANCEL_COLOR_UNKNOWN = "cancel.color_unknown"
CANCEL_TOO_LATE = "cancel.too_late"

# Chat
CHAT_AI_UNAVAILABLE = "chat.ai_unavailable"
CHAT_EMPTY = "chat.empty"
CHAT_RATE_LIMIT = "chat.rate_limit"
CHAT_TOO_FAST = "chat.too_fast"
CHAT_DUPLICATE = "chat.duplicate"

# Session / AI
AI_NO_MOVE = "ai.no_move"
MOVE_IMPOSSIBLE = "move.impossible"

# WS protocol
WS_INVALID_JSON = "ws.invalid_json"
WS_EXPECTED_OBJECT = "ws.expected_object"
WS_UNKNOWN_COMMAND = "ws.unknown_command"
WS_UNKNOWN_MESSAGE = "ws.unknown_message"
WS_GAME_OVER = "ws.game_over"
WS_NOT_YOUR_TURN = "ws.not_your_turn"
WS_INVALID_MOVE_DATA = "ws.invalid_move_data"


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if not params:
        return None
    return params


def ws_payload(code: str, **params: Any) -> dict:
    out: dict = {"message_code": code}
    cleaned = _clean_params(params)
    if cleaned:
        out["message_params"] = cleaned
    return out


def ws_error(code: str, **params: Any) -> dict:
    return {"status": "error", **ws_payload(code, **params)}


def ws_user_message(code: str, **params: Any) -> dict:
    return ws_payload(code, **params)
