#!/usr/bin/env bash
# Production deploy on the VPS: pull main and rebuild containers.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

BRANCH="${DEPLOY_BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

echo "==> Shatra deploy in $REPO_ROOT (branch $BRANCH)"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not a git repository: $REPO_ROOT" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 required (docker compose)." >&2
  exit 1
fi

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

docker compose -f "$COMPOSE_FILE" up -d --build

echo "==> Deploy finished"
docker compose -f "$COMPOSE_FILE" ps
