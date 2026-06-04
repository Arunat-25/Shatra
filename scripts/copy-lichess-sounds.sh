#!/usr/bin/env bash
# Download AGPL-licensed piano sounds from lichess-org/lila (see docs/SOUNDS.md).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/frontend/public/sounds/piano"
BASE="https://raw.githubusercontent.com/lichess-org/lila/master/public/sound/piano"

FILES=(
  Move.ogg
  Capture.ogg
  Victory.ogg
  Defeat.ogg
  Draw.ogg
  GenericNotify.ogg
  NewChallenge.ogg
  NewPM.ogg
  LowTime.ogg
)

mkdir -p "$DEST"

for f in "${FILES[@]}"; do
  echo "Fetching $f ..."
  curl -fsSL "$BASE/$f" -o "$DEST/$f"
done

echo "Done. $(wc -c <(cat "$DEST"/*.ogg) | awk '{print $1}') bytes in $DEST"
