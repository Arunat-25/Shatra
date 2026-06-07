# Шатра

Онлайн-версия алтайской настольной игры «Шатра»: мультиплеер, игра с ботом, таймеры.

## Требования

- Python 3.11+
- Node.js 18+
- Redis и PostgreSQL (локально или через Docker)

## Быстрый старт (Docker)

```bash
docker compose up --build -d
```

Откройте http://127.0.0.1:8000 — приложение, PostgreSQL и Redis в контейнерах.  
При сборке образа фронтенд собирается автоматически (`npm run build` внутри Docker).  
Миграции БД применяются при старте контейнера `app` (`alembic upgrade head`).

Перед первым запуском задайте `JWT_SECRET` в `.env` (см. ниже).

### Доступ через интернет (Cloudflare Tunnel)

Для короткого теста с друзьями из другой сети — без деплоя и без своего домена:

```bash
# Установите cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
./scripts/tunnel-quick.sh
```

Скрипт поднимает Docker и выводит публичный URL вида `https://....trycloudflare.com`.  
Отправьте эту ссылку — WebSocket и API работают через тот же хост автоматически.

Ограничения quick tunnel: URL меняется при каждом перезапуске, ноутбук должен быть включён, терминал с туннелем не закрывать.

Если туннель не открывается (ошибка 530), в сети может блокироваться QUIC — скрипт использует `--protocol http2` для обхода.

## Локальная разработка

```bash
cp .env.example .env   # опционально

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && npm run build && cd ..

# Redis и PostgreSQL
docker compose up redis postgres -d
alembic upgrade head

# Сервер (нужен JWT_SECRET в .env)
uvicorn main:app --reload
```

Откройте http://127.0.0.1:8000

### Разработка фронтенда

```bash
cd frontend
npm run dev
```

Vite проксирует `/rooms` и `/ws` на backend (`API_HOST` в `vite.config.js`, по умолчанию `localhost:8000`).

Звуки игры — сэмплы из [lila](https://github.com/lichess-org/lila) (набор piano, AGPL). См. [docs/SOUNDS.md](docs/SOUNDS.md). Обновить файлы: `./scripts/copy-lichess-sounds.sh`.

## Конфигурация

Переменные окружения (см. [.env.example](.env.example)):

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DB` | Подключение к Redis | `localhost:6379/0` |
| `REDIS_URL` | Альтернатива отдельным полям | — |
| `REDIS_TTL_SECONDS` | TTL ключей room/game | 14400 |
| `DISCONNECT_TIMEOUT` | Ожидание реконнекта (сек) | 30 |
| `CORS_ALLOW_ORIGINS` | CORS | `*` |
| `SENTRY_DSN` | Мониторинг ошибок (опционально) | — |
| `DATABASE_URL` | PostgreSQL (asyncpg) | `postgresql+asyncpg://shatra:shatra@localhost:5432/shatra` |
| `JWT_SECRET` | Секрет для JWT | *(обязательно сменить)* |
| `ADMIN_USER_IDS` | UUID админов через запятую (без правки БД) | — |

### Админ-панель

- URL: `/admin` (только для пользователей с `is_admin` в БД или UUID в `ADMIN_USER_IDS`).
- Назначить админа в БД: `UPDATE users SET is_admin = TRUE WHERE username = '...';`
- Либо добавить UUID в `.env`: `ADMIN_USER_IDS=uuid1,uuid2`
- API: `GET /api/admin/stats/registrations`, `/online`, `/games`
- **Онлайн** учитывает WS в комнате и polling лобби (`GET /rooms?client_id=...`, TTL 25 с)

### Аккаунты

- Регистрация: `/register` — имя пользователя и пароль (русские буквы в username допускаются).
- Вход: `/login` — имя пользователя и пароль.
- Профиль: `/profile` — имя, фамилия, район (опционально).
- **Восстановление пароля не предусмотрено** — при забытом пароле доступ к профилю теряется.
- Игра в лобби **без входа** по-прежнему доступна.

## Тесты

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt

# Один раз (если postgres уже был без init-скрипта):
./scripts/ensure-test-db.sh

pytest tests/ -q
cd frontend && npm test
```

Pytest использует **отдельную БД** `shatra_test` и **Redis DB 1** (см. `tests/test_env.py`), чтобы не затирать dev-данные в `shatra` / Redis DB 0.

Структура: [tests/README.md](tests/README.md).

## Линт

```bash
ruff check backend/ game_engine/ main.py
cd frontend && npm run lint
```

CI: GitHub Actions (`.github/workflows/ci.yml`) — pytest, ruff, vitest, eslint.

## Архитектура (кратко)

- `game_engine/` — чистая логика правил (без I/O)
- `backend/` — FastAPI, WebSocket, Redis, таймеры, AI
- `frontend/` — React + Vite

Доменные типы фигур: `game_engine/domain.py`. Состояние игры в Redis: `backend/game_state.py`.
