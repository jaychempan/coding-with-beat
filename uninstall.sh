#!/usr/bin/env bash
# Remove CC-Jukebox entries from ~/.claude/settings.json and the global symlink.
# Leaves ~/.cc-jukebox data alone unless you pass --purge (which also drops the venv).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$HOME/.cc-jukebox/venv/bin/python"
SETTINGS_FILE="$HOME/.claude/settings.json"
LINK="$HOME/.local/bin/cc-jukebox"

# 1. drop ~/.claude/settings.json entries (need the venv's python to run the script)
if [ -x "$VENV_PY" ]; then
  "$VENV_PY" "$REPO/scripts/install_settings.py" \
    --settings "$SETTINGS_FILE" \
    --python   "$VENV_PY" \
    --repo     "$REPO" \
    --remove
  echo "✓ removed cc-jukebox from $SETTINGS_FILE"
else
  echo "! venv missing at $VENV_PY — skipping settings cleanup. Run install.sh first if you need it."
fi

# 2. remove the global symlink (only if it's actually ours)
if [ -L "$LINK" ]; then
  rm "$LINK"
  echo "✓ removed $LINK"
elif [ -e "$LINK" ]; then
  echo "! $LINK exists but is not a symlink — leaving it alone."
fi

# 3. optional purge
if [ "${1:-}" = "--purge" ]; then
  rm -rf "$HOME/.cc-jukebox"
  echo "✓ purged ~/.cc-jukebox/ (data + venv)"
fi
