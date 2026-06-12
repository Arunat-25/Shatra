#!/bin/sh
set -e

# Share built /assets with nginx (gzip_static) via named volume.
if [ -d /app/frontend/dist/assets ] && [ -d /shatra-static ]; then
  mkdir -p /shatra-static/assets
  cp -a /app/frontend/dist/assets/. /shatra-static/assets/
fi

alembic upgrade head
exec uvicorn main:app --host 0.0.0.0 --port 8000
