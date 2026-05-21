#!/usr/bin/env bash
# CC-Jukebox installer — idempotent. Re-run safely after edits.
#
# What this does:
#   1. Creates a user-level venv at ~/.cc-jukebox/venv with the best
#      Python ≥3.10 it can find.
#   2. Installs cc-jukebox into that venv in editable mode (pip install -e .),
#      which also registers the `cc-jukebox` console script.
#   3. Symlinks `cc-jukebox` into ~/.local/bin/ so it's globally callable.
#   4. Registers the MCP server, statusline, and hooks with Claude Code
#      by merging into ~/.claude/settings.json.
#
# Re-run anytime; existing settings keys are updated in place.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "\033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "\033[33m!\033[0m %s\n" "$1"; }
die()  { printf "\033[31m✗ %s\033[0m\n" "$1" >&2; exit 1; }

bold "CC-Jukebox installer"
echo "  repo:   $REPO"
echo "  venv:   $HOME/.cc-jukebox/venv"
echo "  bin:    $HOME/.local/bin/cc-jukebox"

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

# 2. venv at ~/.cc-jukebox/venv
VENV="$HOME/.cc-jukebox/venv"
mkdir -p "$HOME/.cc-jukebox"
if [ ! -d "$VENV" ]; then
  "$PY" -m venv "$VENV"
  ok "created venv at $VENV"
else
  ok "venv exists at $VENV"
fi
VENV_PY="$VENV/bin/python"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -e "$REPO"
ok "installed cc-jukebox (editable) + deps"

# 3. symlink ~/.local/bin/cc-jukebox
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
LINK="$BIN_DIR/cc-jukebox"
TARGET="$VENV/bin/cc-jukebox"
[ -x "$TARGET" ] || die "expected $TARGET to exist after pip install; aborting."
# replace symlink if it exists (even broken). Refuse to clobber a real file.
if [ -L "$LINK" ] || [ ! -e "$LINK" ]; then
  ln -sfn "$TARGET" "$LINK"
  ok "linked $LINK -> $TARGET"
elif [ -f "$LINK" ]; then
  warn "$LINK is a regular file, not a symlink — leaving it alone."
  warn "Remove it manually and re-run, or add $TARGET to PATH yourself."
fi

# PATH check
case ":$PATH:" in
  *":$BIN_DIR:"*) ok "$BIN_DIR is on PATH" ;;
  *) warn "$BIN_DIR is NOT on PATH. Add this to ~/.zshrc:"
     echo '    export PATH="$HOME/.local/bin:$PATH"' ;;
esac

# 4. patch ~/.claude/settings.json
SETTINGS_DIR="$HOME/.claude"
SETTINGS_FILE="$SETTINGS_DIR/settings.json"
mkdir -p "$SETTINGS_DIR"

"$VENV_PY" "$REPO/scripts/install_settings.py" \
  --settings "$SETTINGS_FILE" \
  --python   "$VENV_PY" \
  --repo     "$REPO"

ok "Claude Code settings patched: $SETTINGS_FILE"

# 5. Make sure data dir exists
"$VENV_PY" -c "from cc_jukebox.config import ensure_dirs; ensure_dirs()"
ok "data dir ready: ~/.cc-jukebox/"

echo
bold "Done. Try these from any directory:"
echo "  cc-jukebox banner"
echo "  cc-jukebox status"
echo "  cc-jukebox player"
echo
echo "Then start a new Claude Code session — the MCP server registers as 'cc-jukebox'."
echo "Inside CC, try: \"play some lofi\" or \"show the player\"."
echo
warn "To remove: ./uninstall.sh   (add --purge to also delete ~/.cc-jukebox)"
