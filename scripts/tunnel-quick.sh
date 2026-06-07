#!/bin/sh
set -e
cd "$(dirname "$0")/.."

if ! command -v cloudflared >/dev/null 2>&1; then
  if [ -x "$HOME/.local/bin/cloudflared" ]; then
    PATH="$HOME/.local/bin:$PATH"
  else
    echo "cloudflared not found. Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/"
    exit 1
  fi
fi

docker compose up -d
echo "Локально: http://127.0.0.1:8000"
echo "Публичный URL появится ниже (trycloudflare.com):"
exec cloudflared tunnel --protocol http2 --url http://127.0.0.1:8000
