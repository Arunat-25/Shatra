# Рефакторинг: итоговый чеклист

## Backend
- [x] `backend/state.py` — единое хранилище games, game_timers, disconnect_timers
- [x] `backend/timers.py` — game_ticker, disconnect_timer, stop_game_timer
- [x] `backend/game_session.py` — handle_ai_move, websocket_endpoint
- [x] `backend/schemas.py` — GameState, WSMessage, ClientMessage (TypedDict)
- [x] `backend/ws_manager.py` — циклические импорты убраны, импорт из state
- [x] `main.py` — сокращён, WS-логика вынесена

## game_engine
- [x] `game_engine/validation.py` — validate_move, get_all_mandatory_captures, find_captured_enemy
- [x] `game_engine/moves.py` — process_move, execute_move, _promote_shatra
- [x] `game_engine/endgame.py` — is_game_over, add_to_history
- [x] `game_engine/hints.py` — get_hints, подсказки по цепочкам
- [x] `game_engine/game_logic.py` — фасад с делегированием (включая get_hints)

## Frontend
- [x] `frontend/src/components/TimerPicker.jsx` — вынесен из Lobby
- [x] `frontend/src/components/DisconnectOverlay.jsx` — вынесен из Game
- [x] `frontend/src/Lobby.jsx` — использует TimerPicker, убран dead code
- [x] `frontend/src/Game.jsx` — использует DisconnectOverlay, убран лишний импорт
- [x] `frontend/src/components/GameHeader.jsx` — PropTypes
- [x] `frontend/src/components/GameInfo.jsx` — PropTypes
- [x] `prop-types` установлен как зависимость

## Проверки
- [x] python3 -c "from main import app" — OK
- [x] vite build — OK (50 modules)
- [x] curl /rooms — OK
- [x] ai.py — get_hints воссоздан в GameLogic