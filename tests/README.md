# Тесты Shatra

## Запуск

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt

# Один раз, если postgres поднят без свежего volume:
./scripts/ensure-test-db.sh

pytest tests/ -q
cd frontend && npm test
```

**Изоляция от dev:** pytest подключается к `shatra_test` (PostgreSQL) и Redis DB `1`, а не к рабочей базе `shatra` / Redis DB `0`. Настройки — `tests/test_env.py`, переменная `TEST_DATABASE_URL`.

| Каталог | Что проверяют |
|---------|---------------|
| `tests/admin/test_admin_e2e.py` | E2E: регистрация/игры/онлайн через API+WS → admin stats |

С покрытием: `pytest tests/ --cov=backend --cov=game_engine -q`

## Структура

| Каталог / файлы | Что проверяют |
|-----------------|---------------|
| `tests/server/` | REST комнат, WS connect, цвета, реванш/ничья, таймеры, история, edge-cases |
| `tests/server/test_edge_cases.py` | Ключи доски str/int, отклонённые ходы, история, инкремент |
| `tests/server/test_ws_connect.py` | Дубль вкладки, переподключение, фильтр лобби |
| `tests/server/test_timer_metrics.py` | Метрики таймаутов (clock / disconnect) |
| `tests/observability/` | Unit: middleware, logging, metrics helpers, Sentry wrapper |
| `tests/observability/test_grafana_dashboard.py` | Регрессия: PromQL в `shatra.json` не скрывает редкие счётчики |
| `tests/observability/test_promql_semantics.py` | Модель: `increase()` = 0 при flat counter, `_total` ≥ 1 |
| `tests/observability/test_metrics_dashboard_alignment.py` | Запросы панелей Grafana vs текст `/metrics` |
| `tests/observability/test_redis_metrics.py` | Gauge комнат/игр в Redis (scan-on-scrape) |
| `tests/observability/test_prometheus_alerts.py` | Регрессия правил в `docker/prometheus/alerts.yml` |
| `tests/test_observability.py` | Endpoint smoke: `/health`, `/metrics` |
| `tests/integration/test_observability_e2e.py` | E2E: REST/WS сценарии → Prometheus, live `/health` |
| `tests/server/test_timers_edge.py` | Таймаут, disconnect, коррекция часов после паузы |
| `tests/test_domain.py` | Enum Color/PieceType, parse/format фигур |
| `tests/server/test_game_state.py` | Pydantic GameState |
| `tests/server/test_memory_cleanup.py` | Утечки: game_timers, disconnect_timers, locks, connections |
| `tests/server/test_game_session_integration.py` | WS: ничья, реванш, ходы, AI, disconnect |
| `tests/server/test_finished_game_cleanup.py` | Матрица cleanup Redis после `game_over` (unit + полустек) |
| `tests/integration/test_finished_game_cleanup_e2e.py` | E2E: ключи Redis и gauge после cleanup |
| `tests/server/test_game_ticker.py` | Тикер: только активные часы |
| `frontend/src/*.test.js` | Vitest: reconnect, messageHandlers, reducer |
| `tests/auth/` | Регистрация, вход, JWT, срок жизни токенов, профиль, refresh/logout |
| `tests/auth/test_auth_tokens.py` | Истечение access/refresh, цепочка refresh, неверная подпись |
| `tests/conftest.py` | Общие фикстуры (доска, комната, игра) |
| `tests/test_game_logic.py` | Движок: ходы, взятия, подсказки |
| `tests/test_*.py` | Фигуры, доска, AI, интеграционные сценарии |

Папка названа `server`, а не `backend`, чтобы не перекрывать импорт пакета `backend`.
