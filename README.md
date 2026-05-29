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
pytest tests/ -q
cd frontend && npm test
```

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
