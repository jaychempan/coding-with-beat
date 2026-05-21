#!/usr/bin/env bash
# CC-Jukebox installer — idempotent. Re-run safely after edits.
#
# What this does:
#   1. Creates .venv with the best Python ≥3.10 it can find.
#   2. Installs the runtime deps (mcp, Pillow, rich, mutagen, httpx).
#   3. Registers the MCP server, statusline, and hooks with Claude Code
#      by merging into ~/.claude/settings.json (Python script handles merge).
#   4. Prints next steps.
#
# Re-run anytime; existing settings keys are updated in place.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "\033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "\033[33m!\033[0m %s\n" "$1"; }
die()  { printf "\033[31m✗ %s\033[0m\n" "$1" >&2; exit 1; }

bold "CC-Jukebox installer"
echo "  repo: $REPO"

# 1. find a Python ≥3.10
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 \
            "$HOME/miniconda3/envs/dlbase/bin/python" \
            "$(command -v python3 2>/dev/null || true)"; do
  [ -z "$cand" ] && continue
  if command -v "$cand" >/dev/null 2>&1 || [ -x "$cand" ]; then
    v="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
    case "$v" in
      3.1[0-9]|3.[2-9][0-9]) PY="$cand"; break ;;
    esac
  fi
done
[ -n "$PY" ] || die "no Python ≥3.10 found. Install one (brew install python@3.11) and re-run."
ok "python: $PY ($($PY --version))"

# 2. venv + deps
if [ ! -d "$REPO/.venv" ]; then
  "$PY" -m venv "$REPO/.venv"
  ok "created venv"
else
  ok "venv exists"
fi
"$REPO/.venv/bin/pip" install --quiet --upgrade pip
"$REPO/.venv/bin/pip" install --quiet "mcp>=1.0.0" "Pillow>=10.0" "rich>=13.0" "mutagen>=1.47" "httpx>=0.27"
ok "deps installed"

VENV_PY="$REPO/.venv/bin/python"

# 3. patch ~/.claude/settings.json
SETTINGS_DIR="$HOME/.claude"
SETTINGS_FILE="$SETTINGS_DIR/settings.json"
mkdir -p "$SETTINGS_DIR"

"$VENV_PY" "$REPO/scripts/install_settings.py" \
  --settings "$SETTINGS_FILE" \
  --python   "$VENV_PY" \
  --repo     "$REPO"

ok "Claude Code settings patched: $SETTINGS_FILE"

# 4. Make sure data dir exists
"$VENV_PY" -c "from cc_jukebox.config import ensure_dirs; ensure_dirs()"
ok "data dir ready: ~/.cc-jukebox/"

echo
bold "Done. Try these:"
echo "  $VENV_PY -m cc_jukebox banner"
echo "  $VENV_PY -m cc_jukebox demo"
echo "  $VENV_PY -m cc_jukebox status"
echo
echo "Then start a new Claude Code session — the MCP server registers as 'cc-jukebox'."
echo "Inside CC, try: \"play some lofi\" or \"show the player\"."
echo
warn "To remove: ./uninstall.sh"
