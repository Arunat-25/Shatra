# Мониторинг Shatra

Дашборд **Shatra** в Grafana (`docker/grafana/dashboards/shatra.json`) обновляется каждые 30 секунд.  
Источники данных: **Prometheus** (метрики с `GET /metrics`), **PostgreSQL** (таблица `finished_games`) и **Loki** (логи контейнеров, Explore).

Доступ при `docker compose up`:

| Сервис | URL | Логин |
|--------|-----|-------|
| Grafana | http://127.0.0.1:3000 | `admin` / `GRAFANA_ADMIN_PASSWORD` (по умолчанию `admin`) |
| Prometheus | http://127.0.0.1:9090 | — |
| Alerts | http://127.0.0.1:9090/alerts | — |
| Метрики app | http://127.0.0.1:8000/metrics | — |
| Health | http://127.0.0.1:8000/health | — |
| Loki | внутри compose (`loki:3100`) | логи → Grafana **Explore** → datasource **Loki** |

---

## Роли инструментов

| Инструмент | Для чего |
|------------|----------|
| **Prometheus + Grafana** | Метрики: WS, HTTP, игры, Redis, длительность партий |
| **Loki** | Поток логов из Docker (stdout), поиск по `request_id`, `room_id` |
| **Sentry** | Ошибки со stack trace (backend + frontend), алерты по issue |

Loki не заменяет Sentry. Для корреляции: возьмите `request_id` из Sentry или заголовка `X-Request-ID` и найдите его в Loki.

---

## Логи (Loki)

Promtail собирает stdout всех контейнеров compose через Docker socket. Логи `shatra-app` — **JSON** (`LOG_FORMAT=json`); поля `level`, `logger`, `message`, `request_id`, `service`.

**Просмотр:** Grafana → **Explore** → datasource **Loki**.

Примеры LogQL:

```logql
{container="shatra-app"}
```

```logql
{container="shatra-app"} | json | level="ERROR"
```

```logql
{container="shatra-app"} | json | request_id="abc-123-from-x-request-id"
```

```logql
{container="shatra-app"} |= "room" | json
```

Проверка после старта:

```bash
curl -s http://127.0.0.1:8000/health
# в Explore: {container="shatra-app"} |= "/health"
```

Retention Loki: **7 дней** (`docker/loki/loki-config.yml`). Для text-логов (`LOG_FORMAT=text`) JSON-фильтры в LogQL не работают — в Docker держите `json`.

---

## Как читать метрики

**Counter (`*_total`)** — только растёт с момента старта процесса. На дашборде для редких событий (игры, комнаты) показывается **текущее значение счётчика**, а не `increase(...[1h])`: после одной партии счётчик остаётся на 1, и `increase` за час даст 0.

**Gauge** — текущее значение «здесь и сейчас» (например, сколько ключей в Redis).

**Histogram** — распределение (длительность партии, число ходов). Для них `rate(..._bucket)` корректен.

**Rate / increase с коротким окном (5m, 15m)** — подходит для частых событий: HTTP, ходы, WS-события.

---

## Панели дашборда (сверху вниз)

### Ряд 1 — инфраструктура и HTTP

| Панель | Что показывает | Метрика / запрос |
|--------|----------------|------------------|
| **Active WebSocket connections** | Сколько WS-соединений сейчас открыто (игроки в комнатах). Падает при disconnect, растёт при connect. | `shatra_ws_connections_active` |
| **HTTP request rate** | Среднее число HTTP-запросов в секунду за последние 5 минут (REST: комнаты, auth, health и т.д.). | `sum(rate(http_requests_total[5m]))` |
| **HTTP latency p95** | 95-й перцентиль времени ответа HTTP за 5 минут. Высокие значения — тормоза API или БД. | p95 по `http_request_duration_seconds_bucket` |

### Ряд 2 — игры (накопительно с перезапуска app)

| Панель | Что показывает | Метрика / запрос |
|--------|----------------|------------------|
| **Games finished (total since app start)** | Сколько партий **завершено и успешно заархивировано**, по причинам: `resign`, `timeout`, `biy_wins`, `draw_agreed`, `opponent_disconnected` и др. Линии по `reason`. | `sum by (reason) (shatra_games_finished_total)` |
| **Rooms created / games started (total)** | Две кривые: сколько комнат **создали** и сколько партий **фактически начали** (второй игрок / старт vs AI). Не путать с «комнат в Redis сейчас». | `sum(shatra_rooms_created_total)`, `sum(shatra_games_started_total)` |

### Ряд 3 — WebSocket

| Панель | Что показывает | Метрика / запрос |
|--------|----------------|------------------|
| **WebSocket events (15m rate)** | Сколько WS-событий произошло за последние 15 минут: connect, disconnect, reject (комната полна, уже в игре и т.д.). Разбивка по `event` и `reason`. | `increase(shatra_ws_events_total[15m])` |

### Ряд 4 — Redis (текущее состояние)

Обновляется при каждом scrape `/metrics` (scan ключей `room:*` и `game:*`).

После `game_over` ключи удаляются из Redis, когда **никого не осталось на WebSocket** (реванш возможен, пока оба игрока ещё подключены). Если `game_over=true` долго висит на графике — комната не была очищена (старые данные до фикса или обрыв без disconnect).

| Панель | Что показывает | Метрика / запрос |
|--------|----------------|------------------|
| **Redis rooms (current)** | Сколько ключей `room:*` **сейчас** в Redis, по типу: `public`, `private`, `ai`. | `sum by (room_type) (shatra_redis_rooms_active)` |
| **Redis games (current)** | Сколько ключей `game:*` в Redis; `game_over=false` — партия идёт, `true` — завершена, но ключ ещё не удалён. | `sum by (game_over) (shatra_redis_games_active)` |
| **Public rooms waiting for opponent** | Публичные комнаты, где игра **ещё не началась** (ожидают второго игрока). Близко к «лobby» в UI. | `shatra_redis_rooms_waiting{room_type="public"}` |

Если комнаты растут без игроков — смотрите alert **ShatraRedisRoomsLeak** и скрипт `scripts/redis_inventory.py`.

### Ряд 5 — ходы

| Панель | Что показывает | Метрика / запрос |
|--------|----------------|------------------|
| **Moves rate** | Принятые ходы в секунду (игрок + AI). | `sum(rate(shatra_moves_total[5m]))` |
| **Rejected moves rate** | Отклонённые попытки хода в секунду по причинам (`move.impossible`, неверный цвет и т.д.). Всплеск — баг клиента или рассинхрон состояния. | `sum by (reason) (rate(shatra_moves_rejected_total[5m]))` |

### Ряд 6 — итоги, сверка, качество

| Панель | Что показывает | Метрика / запрос |
|--------|----------------|------------------|
| **Timeouts (total)** | Партии, закончившиеся по таймеру или disconnect-forfeit, с момента старта app. Типы: `clock`, `disconnect`. | `sum by (type) (shatra_timeouts_total)` |
| **Archive errors (total)** | Сколько раз **не удалось** сохранить партию в PostgreSQL. Должно быть **0**. Красный порог при ≥ 1. | `sum(shatra_archive_errors_total)` |
| **Games finished — Prometheus total** | Общее число заархивированных партий по метрикам (все `reason` вместе). | `sum(shatra_games_finished_total)` |
| **Games archived (last 1h, Postgres)** | Сколько строк реально попало в таблицу `finished_games` за последний час. **Ground truth** из БД. | SQL к Postgres |

**Сверка:** после игры «Prometheus total» (за всё время с перезапуска) и «Postgres last 1h» (за час) смотрят на разные окна. Для одной свежей партии: Prometheus total ≥ 1 и Postgres last 1h ≥ 1. Если Prometheus растёт, а Postgres — нет, смотрите **Archive errors**.

### Ряд 7 — длительность партий

| Панель | Что показывает | Метрика / запрос |
|--------|----------------|------------------|
| **Game duration p95 / plies p50** | Две кривые: **p95** длительности партии в секундах и **p50** числа полуходов (plies) за последний час. Данные пишутся только при успешном архиве. Пустой график — ещё не было заархивированных игр после деплоя. | `shatra_game_duration_seconds_bucket`, `shatra_game_plies_bucket` |

---

## Prometheus alerts

Правила: `docker/prometheus/alerts.yml`. Уведомления никуда не отправляются — только UI.

| Alert | Когда срабатывает |
|-------|-------------------|
| **ShatraTargetDown** | Prometheus не может scrape `app:8000/metrics` 1 минуту |
| **ShatraArchiveErrors** | За 15 мин был хотя бы один `shatra_archive_errors_total` |
| **ShatraHighMoveRejectRate** | > 0.5 rejected moves/s в среднем за 5 минут |
| **ShatraRedisRoomsLeak** | Сумма `shatra_redis_rooms_active` > 50 дольше 15 минут |

---

## Коды `reason` для завершённых игр

| `reason` | Значение |
|----------|----------|
| `resign` | Сдача |
| `timeout` | Флаг по часам |
| `opponent_disconnected` | Победа из-за disconnect соперника |
| `draw_agreed` | Ничья по согласию |
| `biy_wins` | Победа на доске (остался один бий) |
| `draw_repetition` / `draw_two_biys` | Ничья по правилам движка |
| `ai.no_move` | AI не смог сходить |
| `cancelled` | Не архивируется, в finished metrics не попадает |

---

## Полезные команды

```bash
# Сырой текст метрик
curl -s http://127.0.0.1:8000/metrics | grep shatra_

# Инвентаризация Redis (комнаты/игры)
python scripts/redis_inventory.py

# Тесты observability
pytest tests/observability/ tests/integration/test_observability_e2e.py -q
```

---

## Sentry (backend)

Проверка интеграции в dev: `GET http://127.0.0.1:8000/sentry-debug` — намеренный `ZeroDivisionError`. Маршрут доступен только при `APP_ENV=development` и непустом `SENTRY_DSN`.

Если в Sentry по-прежнему «Waiting for this project's first error», открой **Project Settings → Client Keys (DSN)** и скопируй **новый DSN** в `.env`:

- `SENTRY_DSN` — backend (runtime в Docker)
- `VITE_SENTRY_DSN` — frontend (build-time; после смены пересобери образ: `docker compose up --build`)

Sentry отклоняет события с `403 … ProjectId`, если DSN от другого проекта или устарел после пересоздания проекта — это не «верификация», а неверный ключ.

Опциональный e2e-тест `test_prometheus_scrape_matches_app_games_finished_when_available` **пропускается**, если Prometheus не запущен или ещё не собрал метрики — это нормально при `pytest` только с postgres/redis.
