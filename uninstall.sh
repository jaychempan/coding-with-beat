#!/usr/bin/env bash
# Remove coding-with-beat: settings entries, global symlink, slash command, and PATH block.
# Leaves ~/.coding-with-beat data alone unless you pass --purge (which also drops the venv).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$HOME/.coding-with-beat/venv/bin/python"
SETTINGS_FILE="$HOME/.claude/settings.json"
LINK="$HOME/.local/bin/cwb"
CMD_LINK="$HOME/.claude/commands/cwb.md"
MCP_LABEL="com.coding-with-beat.server"
MCP_PLIST="$HOME/Library/LaunchAgents/$MCP_LABEL.plist"
MCP_URL_FILE="$HOME/.coding-with-beat/mcp-url"

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

# 3. remove the /cwb slash command (only if it's our symlink)
if [ -L "$CMD_LINK" ]; then
  rm "$CMD_LINK"
  echo "✓ removed $CMD_LINK"
elif [ -e "$CMD_LINK" ]; then
  echo "! $CMD_LINK is not a symlink — leaving it alone."
fi

# 4. remove cwb skills symlinks from ~/.claude/skills/
SKILLS_DST_DIR="$HOME/.claude/skills"
for skill_name in cwb cwb-chinese cwb-classical cwb-focus cwb-hype cwb-jazz cwb-lofi cwb-party cwb-relax cwb-sad cwb-sleep cwb-synthwave; do
  skill_dst="$SKILLS_DST_DIR/$skill_name"
  if [ -L "$skill_dst" ]; then
    rm "$skill_dst"
    echo "✓ removed skill symlink $skill_dst"
  fi
done

# 5. strip the cwb block from ~/.claude/CLAUDE.md
GLOBAL_CLAUDE_MD="$HOME/.claude/CLAUDE.md"
if [ -f "$GLOBAL_CLAUDE_MD" ] && grep -q ">>> coding-with-beat >>>" "$GLOBAL_CLAUDE_MD"; then
  awk '/# >>> coding-with-beat >>>/{found=1} !found{print} /# <<< coding-with-beat <<</{found=0}' \
    "$GLOBAL_CLAUDE_MD" > "$GLOBAL_CLAUDE_MD.tmp" && mv "$GLOBAL_CLAUDE_MD.tmp" "$GLOBAL_CLAUDE_MD"
  echo "✓ removed coding-with-beat block from $GLOBAL_CLAUDE_MD"
fi

# 7. strip the marked PATH block from ~/.zshrc and ~/.bashrc
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

# 8. stop and remove the macOS HTTP MCP LaunchAgent
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
  OLD_MCP_PLIST="$HOME/Library/LaunchAgents/com.cc-jukebox.server.plist"
  launchctl bootout "gui/$(id -u)" "$OLD_MCP_PLIST" >/dev/null 2>&1 || true
  if [ -f "$OLD_MCP_PLIST" ]; then
    rm "$OLD_MCP_PLIST"
    echo "✓ removed $OLD_MCP_PLIST"
  fi
fi

# 9. remove persisted MCP URL used by CLI commands
if [ -f "$MCP_URL_FILE" ]; then
  rm "$MCP_URL_FILE"
  echo "✓ removed $MCP_URL_FILE"
fi

# 10. optional purge
if [ "${1:-}" = "--purge" ]; then
  rm -rf "$HOME/.coding-with-beat"
  echo "✓ purged ~/.coding-with-beat/ (data + venv)"
fi
