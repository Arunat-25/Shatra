# Шатра

Онлайн-версия алтайской настольной игры «Шатра»: мультиплеер, игра с ботом, таймеры.

## Требования

- Python 3.11+
- Node.js 18+
- Redis (локально: `redis-server` на порту 6379)

## Установка

```bash
# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install && npm run build && cd ..
```

## Запуск

```bash
# Терминал 1 — Redis
redis-server

# Терминал 2 — сервер (раздаёт API и собранный фронт)
source .venv/bin/activate
uvicorn main:app --reload
```

Откройте http://127.0.0.1:8000

### Разработка фронтенда

```bash
cd frontend
npm run dev
```

Vite проксирует `/rooms` и `/ws` на `localhost:8000` (см. `frontend/vite.config.js`, переменная `API_HOST`).

## Тесты

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest tests/ -q
```

Структура тестов: см. [tests/README.md](tests/README.md).

## Линт фронтенда

```bash
cd frontend && npm run lint
```
