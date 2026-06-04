#!/bin/sh
# Однократно создать shatra_test в уже существующем postgres-volume (без пересоздания volume).
set -e
docker compose exec postgres psql -U shatra -d postgres -v ON_ERROR_STOP=1 -c \
  "SELECT 1 FROM pg_database WHERE datname = 'shatra_test'" \
  | grep -q 1 \
  || docker compose exec postgres psql -U shatra -d postgres -v ON_ERROR_STOP=1 -c \
  "CREATE DATABASE shatra_test OWNER shatra;"
echo "Database shatra_test is ready."
