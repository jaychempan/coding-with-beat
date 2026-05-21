#!/usr/bin/env bash
# Remove coding-with-beat: settings entries, global symlink, slash command, and PATH block.
# Leaves ~/.coding-with-beat data alone unless you pass --purge (which also drops the venv).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$HOME/.coding-with-beat/venv/bin/python"
SETTINGS_FILE="$HOME/.claude/settings.json"
LINK="$HOME/.local/bin/cwb"
CMD_LINK="$HOME/.claude/commands/cwb.md"

# 1. drop ~/.claude/settings.json entries
if [ -x "$VENV_PY" ]; then
  "$VENV_PY" "$REPO/scripts/install_settings.py" \
    --settings "$SETTINGS_FILE" \
    --python   "$VENV_PY" \
    --repo     "$REPO" \
    --remove
  echo "✓ removed coding-with-beat from $SETTINGS_FILE"
else
  echo "! venv missing at $VENV_PY — skipping settings cleanup."
fi

# 2. remove the global symlink
if [ -L "$LINK" ]; then
  rm "$LINK"
  echo "✓ removed $LINK"
elif [ -e "$LINK" ]; then
  echo "! $LINK is not a symlink — leaving it alone."
fi

# 3. remove the /juke slash command (only if it's our symlink)
if [ -L "$CMD_LINK" ]; then
  rm "$CMD_LINK"
  echo "✓ removed $CMD_LINK"
elif [ -e "$CMD_LINK" ]; then
  echo "! $CMD_LINK is not a symlink — leaving it alone."
fi

# 4. strip the marked PATH block from ~/.zshrc and ~/.bashrc
strip_path_block() {
  local rc="$1"
  [ -f "$rc" ] || return 0
  if grep -q ">>> coding-with-beat >>>" "$rc"; then
    # Delete lines between (and including) the markers, plus a single blank line before.
    /usr/bin/sed -i.bak '/# >>> coding-with-beat >>>/,/# <<< coding-with-beat <<</d' "$rc"
    rm -f "$rc.bak"
    echo "✓ stripped coding-with-beat PATH block from $rc"
  fi
}
strip_path_block "$HOME/.zshrc"
strip_path_block "$HOME/.bashrc"

# 5. optional purge
if [ "${1:-}" = "--purge" ]; then
  rm -rf "$HOME/.coding-with-beat"
  echo "✓ purged ~/.coding-with-beat/ (data + venv)"
fi
