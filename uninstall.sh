#!/usr/bin/env bash
# Remove CC-Jukebox: settings entries, global symlink, slash command, and PATH block.
# Leaves ~/.cc-jukebox data alone unless you pass --purge (which also drops the venv).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$HOME/.cc-jukebox/venv/bin/python"
SETTINGS_FILE="$HOME/.claude/settings.json"
LINK="$HOME/.local/bin/cc-jukebox"
CMD_LINK="$HOME/.claude/commands/juke.md"
MCP_LABEL="com.cc-jukebox.server"
MCP_PLIST="$HOME/Library/LaunchAgents/$MCP_LABEL.plist"

# 1. drop ~/.claude/settings.json entries
if [ -x "$VENV_PY" ]; then
  "$VENV_PY" "$REPO/scripts/install_settings.py" \
    --settings "$SETTINGS_FILE" \
    --python   "$VENV_PY" \
    --repo     "$REPO" \
    --remove
  echo "✓ removed cc-jukebox from $SETTINGS_FILE"
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
  if grep -q ">>> cc-jukebox >>>" "$rc"; then
    # Delete lines between (and including) the markers, plus a single blank line before.
    /usr/bin/sed -i.bak '/# >>> cc-jukebox >>>/,/# <<< cc-jukebox <<</d' "$rc"
    rm -f "$rc.bak"
    echo "✓ stripped cc-jukebox PATH block from $rc"
  fi
}
strip_path_block "$HOME/.zshrc"
strip_path_block "$HOME/.bashrc"

# 5. stop and remove the macOS HTTP MCP LaunchAgent
if [ "$(uname -s)" = "Darwin" ]; then
  launchctl bootout "gui/$(id -u)" "$MCP_PLIST" >/dev/null 2>&1 || true
  if [ -f "$MCP_PLIST" ]; then
    rm "$MCP_PLIST"
    echo "✓ removed $MCP_PLIST"
  fi
  OLD_MCP_PLIST="$HOME/Library/LaunchAgents/com.cc-jukebox.mcp-http.plist"
  launchctl bootout "gui/$(id -u)" "$OLD_MCP_PLIST" >/dev/null 2>&1 || true
  if [ -f "$OLD_MCP_PLIST" ]; then
    rm "$OLD_MCP_PLIST"
    echo "✓ removed $OLD_MCP_PLIST"
  fi
fi

# 6. optional purge
if [ "${1:-}" = "--purge" ]; then
  rm -rf "$HOME/.cc-jukebox"
  echo "✓ purged ~/.cc-jukebox/ (data + venv)"
fi
