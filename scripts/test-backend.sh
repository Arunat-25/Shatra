#!/bin/sh
# Запуск backend-тестов локально с учётом нестандартного порта Postgres (5433).
# Использование: ./scripts/test-backend.sh [pytest args...]
set -e
cd "$(dirname "$0")/.."
export TEST_DATABASE_URL="postgresql+asyncpg://shatra:shatra@localhost:5433/shatra_test?ssl=disable"
export JWT_SECRET="${JWT_SECRET:-test-secret}"
export APP_ENV=test
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_DB="${REDIS_DB:-1}"
exec .venv/bin/python -m pytest tests/ "$@"
