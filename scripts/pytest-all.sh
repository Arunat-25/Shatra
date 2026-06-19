#!/usr/bin/env bash
# Full pytest including integration (~1043+ tests). One line per test (-v).
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONUNBUFFERED=1

echo "==> Shatra pytest (all): collecting..."
count="$(.venv/bin/pytest --collect-only -q 2>/dev/null | tail -1)"
echo "==> $count"
echo "==> Running (one line per test below)..."

exec .venv/bin/pytest "$@"
