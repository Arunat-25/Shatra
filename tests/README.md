# Тесты Shatra

## Запуск

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -q
cd frontend && npm test
```

С покрытием: `pytest tests/ --cov=backend --cov=game_engine -q`

## Структура

| Каталог / файлы | Что проверяют |
|-----------------|---------------|
| `tests/server/` | REST комнат, WS connect, цвета, реванш/ничья, таймеры, история, edge-cases |
| `tests/server/test_edge_cases.py` | Ключи доски str/int, отклонённые ходы, история, инкремент |
| `tests/server/test_ws_connect.py` | Дубль вкладки, переподключение, фильтр лобби |
| `tests/server/test_timers_edge.py` | Таймаут, disconnect, коррекция часов после паузы |
| `tests/test_domain.py` | Enum Color/PieceType, parse/format фигур |
| `tests/server/test_game_state.py` | Pydantic GameState |
| `tests/server/test_memory_cleanup.py` | Утечки: game_timers, disconnect_timers, locks, connections |
| `tests/server/test_game_session_integration.py` | WS: ничья, реванш, ходы, AI, disconnect |
| `tests/server/test_game_ticker.py` | Тикер: только активные часы |
| `frontend/src/*.test.js` | Vitest: reconnect, messageHandlers, reducer |
| `tests/auth/` | Регистрация, вход, JWT, срок жизни токенов, профиль, refresh/logout |
| `tests/auth/test_auth_tokens.py` | Истечение access/refresh, цепочка refresh, неверная подпись |
| `tests/conftest.py` | Общие фикстуры (доска, комната, игра) |
| `tests/test_game_logic.py` | Движок: ходы, взятия, подсказки |
| `tests/test_*.py` | Фигуры, доска, AI, интеграционные сценарии |

Папка названа `server`, а не `backend`, чтобы не перекрывать импорт пакета `backend`.
