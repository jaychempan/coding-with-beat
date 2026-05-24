#!/usr/bin/env bash
# Remove coding-with-beat from Codex CLI config.
# Leaves ~/.coding-with-beat data alone unless you pass --purge.
# Does NOT touch ~/.claude/ (use uninstall.sh for Claude Code removal).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$HOME/.coding-with-beat/venv/bin/python"
CODEX_DIR="$HOME/.codex"

PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1

ok()   { printf "\033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "\033[33m!\033[0m %s\n" "$1"; }

# 1. Remove ~/.codex/config.toml + hooks.json entries
if [ -x "$VENV_PY" ]; then
  "$VENV_PY" "$REPO/scripts/install_codex_config.py" \
    --python   "$VENV_PY" \
    --repo     "$REPO" \
    --codex-dir "$CODEX_DIR" \
    --remove
  ok "removed coding-with-beat from Codex config"
else
  warn "venv missing at $VENV_PY — skipping config cleanup"
fi

# 2. Remove skill
SKILL_DIR="$CODEX_DIR/skills/cwb"
if [ -d "$SKILL_DIR" ]; then
  rm -rf "$SKILL_DIR"
  ok "removed $SKILL_DIR"
fi

# 3. Strip coding-with-beat block from ~/.codex/AGENTS.md
AGENTS_MD="$CODEX_DIR/AGENTS.md"
if [ -f "$AGENTS_MD" ] && grep -q ">>> coding-with-beat >>>" "$AGENTS_MD"; then
  if [ -x "$VENV_PY" ]; then
    "$VENV_PY" - "$AGENTS_MD" <<'PY'
import sys; path = sys.argv[1]
lines = open(path).readlines()
out, skip = [], False
for line in lines:
    if ">>> coding-with-beat >>>" in line: skip = True
    if not skip: out.append(line)
    if "<<< coding-with-beat <<<" in line: skip = False
open(path, "w").writelines(out)
PY
  else
    python3 - "$AGENTS_MD" <<'PY'
import sys; path = sys.argv[1]
lines = open(path).readlines()
out, skip = [], False
for line in lines:
    if ">>> coding-with-beat >>>" in line: skip = True
    if not skip: out.append(line)
    if "<<< coding-with-beat <<<" in line: skip = False
open(path, "w").writelines(out)
PY
  fi
  ok "removed coding-with-beat block from $AGENTS_MD"
fi

# 4. Stop + remove LaunchAgent (shared with Claude Code install)
MCP_LABEL="com.coding-with-beat.server"
MCP_PLIST="$HOME/Library/LaunchAgents/$MCP_LABEL.plist"
if [ -f "$MCP_PLIST" ] && [ "$(uname -s)" = "Darwin" ]; then
  launchctl bootout "gui/$(id -u)" "$MCP_PLIST" >/dev/null 2>&1 || true
  rm -f "$MCP_PLIST"
  ok "removed LaunchAgent $MCP_LABEL"
fi

# 4. Optionally purge all data
if [ "$PURGE" = "1" ]; then
  rm -rf "$HOME/.coding-with-beat"
  ok "purged ~/.coding-with-beat"
fi

echo
ok "Codex CLI coding-with-beat uninstalled"
[ "$PURGE" = "0" ] && echo "  (data kept at ~/.coding-with-beat — use --purge to also delete it)"
