#!/usr/bin/env bash
# Fast pytest: skips integration e2e and admin browser e2e (~1000 tests, ~3–5 min).
# Each test prints its own line (pytest -v). Do not pipe to tail — it hides output.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONUNBUFFERED=1

IGNORE=(
  --ignore=tests/integration
  --ignore=tests/admin/test_admin_e2e.py
)

echo "==> Shatra pytest (fast): collecting..."
count="$(.venv/bin/pytest "${IGNORE[@]}" --collect-only -q 2>/dev/null | tail -1)"
echo "==> $count"
echo "==> Running (one line per test below)..."

if [[ -n "${PYTEST_PARALLEL:-}" ]]; then
  echo "==> WARNING: parallel mode can deadlock on shared Postgres; use only if you know why."
  exec .venv/bin/pytest "${IGNORE[@]}" -n "$PYTEST_PARALLEL" --dist loadfile "$@"
fi
exec .venv/bin/pytest "${IGNORE[@]}" "$@"
