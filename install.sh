#!/usr/bin/env bash
# coding-with-beat installer — one-click, idempotent.
#
# What this does (re-run anytime; existing entries are updated in place):
#   1. Creates a user-level venv at ~/.coding-with-beat/venv with the best
#      Python ≥3.10 it can find on PATH.
#   2. Installs coding-with-beat into that venv in editable mode, registering
#      the `cwb` console script.
#   3. Symlinks `cwb` into ~/.local/bin/ and makes sure that dir
#      is on your PATH (writes a marked block into ~/.zshrc / ~/.bashrc).
#   4. Symlinks the /cwb slash command into ~/.claude/commands/.
#   5. Registers MCP server, statusline, vibe hooks, and the /cwb
#      UserPromptExpansion hook with Claude Code via ~/.claude/settings.json.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "\033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "\033[33m!\033[0m %s\n" "$1"; }
die()  { printf "\033[31m✗ %s\033[0m\n" "$1" >&2; exit 1; }

bold "coding-with-beat installer"
echo "  repo:    $REPO"
echo "  venv:    $HOME/.coding-with-beat/venv"
echo "  bin:     $HOME/.local/bin/cwb"
echo "  command: $HOME/.claude/commands/cwb.md"

# 1. find a Python ≥3.10
#    Honours $CWB_PYTHON if set; otherwise scans PATH, Homebrew prefixes
#    (Apple Silicon + Intel), and conda envs.
check_py() {
  local cand="$1"
  [ -z "$cand" ] && return 1
  command -v "$cand" >/dev/null 2>&1 || [ -x "$cand" ] || return 1
  local v
  v="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
  case "$v" in
    3.1[0-9]|3.[2-9][0-9]) return 0 ;;
    *) return 1 ;;
  esac
}

PY=""
# explicit override
if [ -n "${CWB_PYTHON:-}" ] && check_py "$CWB_PYTHON"; then
  PY="$CWB_PYTHON"
fi
# PATH
if [ -z "$PY" ]; then
  for cand in python3.13 python3.12 python3.11 python3.10 python3; do
    if check_py "$cand"; then PY="$(command -v "$cand")"; break; fi
  done
fi
# Homebrew (Apple Silicon and Intel)
if [ -z "$PY" ]; then
  for cand in /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10 \
              /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11 /usr/local/bin/python3.10; do
    if check_py "$cand"; then PY="$cand"; break; fi
  done
fi
# Conda envs (best-effort, picks the first matching env)
if [ -z "$PY" ]; then
  for root in "$HOME/miniconda3/envs" "$HOME/anaconda3/envs" "$HOME/miniforge3/envs" "$HOME/mambaforge/envs"; do
    [ -d "$root" ] || continue
    for env in "$root"/*; do
      if check_py "$env/bin/python"; then PY="$env/bin/python"; break 2; fi
    done
  done
fi
# uv bootstrap (no system Python required)
bootstrap_via_uv() {
  local UV_BIN="$HOME/.local/bin/uv"
  if ! command -v uv >/dev/null 2>&1 && [ ! -x "$UV_BIN" ]; then
    bold "No Python ≥3.10 found — installing uv (single-binary Python manager)..."
    if ! command -v curl >/dev/null 2>&1; then
      die "need curl to bootstrap uv. Install curl and re-run (or set CWB_PYTHON=...)."
    fi
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  # uv writes to ~/.local/bin by default; make sure it's on PATH for this script
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  command -v uv >/dev/null 2>&1 || die "uv install failed."
  ok "uv: $(uv --version)"

  # reuse any Python uv already manages; otherwise download 3.12
  local found
  found="$(uv python find 3.12 2>/dev/null || true)"
  if [ -z "$found" ] || [ ! -x "$found" ]; then
    echo "  Downloading Python 3.12 via uv (one-time, ~25MB)..."
    uv python install 3.12
    found="$(uv python find 3.12)"
  fi
  [ -n "$found" ] && [ -x "$found" ] || die "uv python install failed."
  PY="$found"
}

if [ -z "$PY" ]; then
  warn "No Python ≥3.10 found in PATH / Homebrew / conda envs."
  bootstrap_via_uv
fi
ok "python: $PY ($($PY --version))"

# 2. venv at ~/.coding-with-beat/venv
VENV="$HOME/.coding-with-beat/venv"
mkdir -p "$HOME/.coding-with-beat"
if [ ! -d "$VENV" ]; then
  "$PY" -m venv "$VENV"
  ok "created venv at $VENV"
else
  ok "venv exists at $VENV"
fi
VENV_PY="$VENV/bin/python"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -e "$REPO"
ok "installed coding-with-beat (editable) + deps"

# 3. symlink ~/.local/bin/cwb
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
LINK="$BIN_DIR/cwb"
TARGET="$VENV/bin/cwb"
[ -x "$TARGET" ] || die "expected $TARGET to exist after pip install; aborting."
if [ -L "$LINK" ] || [ ! -e "$LINK" ]; then
  ln -sfn "$TARGET" "$LINK"
  ok "linked $LINK -> $TARGET"
elif [ -f "$LINK" ]; then
  warn "$LINK is a regular file, not a symlink — leaving it alone."
fi

# 4. ensure ~/.local/bin is on PATH (write a marked block, idempotent)
inject_path() {
  local rc="$1"
  [ -f "$rc" ] || return 0
  if grep -q ">>> coding-with-beat >>>" "$rc"; then
    return 0  # already there
  fi
  {
    echo ""
    echo "# >>> coding-with-beat >>>"
    echo '# Added by coding-with-beat install.sh. Remove this block (or run uninstall.sh) to revert.'
    echo 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH";; esac'
    echo "# <<< coding-with-beat <<<"
  } >> "$rc"
  ok "added PATH block to $rc"
}
# create ~/.zshrc if missing (macOS default shell is zsh) so PATH actually gets set
[ -f "$HOME/.zshrc" ] || { touch "$HOME/.zshrc"; ok "created empty ~/.zshrc"; }
inject_path "$HOME/.zshrc"
inject_path "$HOME/.bashrc"

case ":$PATH:" in
  *":$BIN_DIR:"*) ok "$BIN_DIR is on PATH in this shell" ;;
  *) warn "Open a new terminal (or 'source ~/.zshrc') so cwb is on PATH." ;;
esac

# 5. install the /cwb slash command (symlink so repo is source of truth)
CMD_DIR="$HOME/.claude/commands"
mkdir -p "$CMD_DIR"
CMD_LINK="$CMD_DIR/cwb.md"
CMD_SRC="$REPO/commands/cwb.md"
[ -f "$CMD_SRC" ] || die "missing $CMD_SRC — repo is incomplete."
if [ -L "$CMD_LINK" ] || [ ! -e "$CMD_LINK" ]; then
  ln -sfn "$CMD_SRC" "$CMD_LINK"
  ok "linked $CMD_LINK -> $CMD_SRC"
else
  warn "$CMD_LINK already exists as a regular file — leaving it alone."
fi

# 6. patch ~/.claude/settings.json
SETTINGS_DIR="$HOME/.claude"
SETTINGS_FILE="$SETTINGS_DIR/settings.json"
mkdir -p "$SETTINGS_DIR"

"$VENV_PY" "$REPO/scripts/install_settings.py" \
  --settings "$SETTINGS_FILE" \
  --python   "$VENV_PY" \
  --repo     "$REPO"

ok "Claude Code settings patched: $SETTINGS_FILE"

# 7. Make sure data dir exists
"$VENV_PY" -c "from coding_with_beat.config import ensure_dirs; ensure_dirs()"
ok "data dir ready: ~/.coding-with-beat/"

echo
"$VENV/bin/cwb" welcome 2>/dev/null || true
echo
bold "From a new shell (or after 'source ~/.zshrc'):"
echo "  cwb player       — open the pixel player"
echo "  cwb watch        — live TUI"
echo "  /cwb play 周杰伦        — drive it from Claude Code"
echo
warn "To remove: ./uninstall.sh   (add --purge to also delete ~/.coding-with-beat)"
