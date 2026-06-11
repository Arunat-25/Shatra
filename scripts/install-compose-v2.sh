#!/bin/sh
# Install Docker Compose v2 CLI plugin (required; v1 docker-compose is not supported).
set -e

COMPOSE_VERSION="${COMPOSE_VERSION:-v2.32.4}"
PLUGIN_DIR="${DOCKER_CONFIG:-$HOME/.docker}/cli-plugins"
PLUGIN_PATH="$PLUGIN_DIR/docker-compose"

if docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 already installed: $(docker compose version)"
  exit 0
fi

if command -v apt-get >/dev/null 2>&1; then
  if apt-cache show docker-compose-plugin >/dev/null 2>&1; then
    echo "Installing docker-compose-plugin from apt..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y docker-compose-plugin
    docker compose version
    exit 0
  fi
fi

echo "Installing Compose plugin to $PLUGIN_PATH ..."
mkdir -p "$PLUGIN_DIR"
arch=$(uname -m)
case "$arch" in
  x86_64) arch=amd64 ;;
  aarch64|arm64) arch=arm64 ;;
esac
url="https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${arch}"
curl -fsSL "$url" -o "$PLUGIN_PATH"
chmod +x "$PLUGIN_PATH"
docker compose version
