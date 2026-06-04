# --- Frontend (Vite) ---
FROM node:22-alpine AS frontend
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Backend (FastAPI) ---
FROM python:3.12-slim AS backend
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY game_engine/ ./game_engine/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY main.py ./
COPY scripts/docker-entrypoint.sh ./scripts/

COPY --from=frontend /app/frontend/dist ./frontend/dist

RUN chmod +x ./scripts/docker-entrypoint.sh

ENV REDIS_HOST=redis \
    REDIS_PORT=6379

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

ENTRYPOINT ["./scripts/docker-entrypoint.sh"]
