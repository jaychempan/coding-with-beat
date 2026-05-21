#!/usr/bin/env bash
# Remove CC-Jukebox entries from ~/.claude/settings.json. Leaves ~/.cc-jukebox
# data alone unless you pass --purge.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$REPO/.venv/bin/python"
SETTINGS_FILE="$HOME/.claude/settings.json"

if [ ! -x "$VENV_PY" ]; then
  echo "venv missing — settings patch script needs it. Re-run install.sh first." >&2
  exit 1
fi

"$VENV_PY" "$REPO/scripts/install_settings.py" \
  --settings "$SETTINGS_FILE" \
  --python   "$VENV_PY" \
  --repo     "$REPO" \
  --remove

echo "✓ removed cc-jukebox from $SETTINGS_FILE"

if [ "${1:-}" = "--purge" ]; then
  rm -rf "$HOME/.cc-jukebox"
  echo "✓ purged ~/.cc-jukebox/"
fi
