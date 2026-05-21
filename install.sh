#!/usr/bin/env bash
# CC-Jukebox installer — one-click, idempotent.
#
# What this does (re-run anytime; existing entries are updated in place):
#   1. Creates a user-level venv at ~/.cc-jukebox/venv with the best
#      Python ≥3.10 it can find on PATH.
#   2. Installs cc-jukebox into that venv in editable mode, registering
#      the `cc-jukebox` console script.
#   3. Symlinks `cc-jukebox` into ~/.local/bin/ and makes sure that dir
#      is on your PATH (writes a marked block into ~/.zshrc / ~/.bashrc).
#   4. Symlinks the /juke slash command into ~/.claude/commands/.
#   5. Registers HTTP MCP server, statusline, vibe hooks, and the /juke
#      UserPromptExpansion hook with Claude Code via ~/.claude/settings.json.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELAY_SOCKET="${CC_JUKEBOX_RELAY_SOCKET:-}"
RELAY_URL="${CC_JUKEBOX_RELAY_URL:-}"
DEFAULT_MCP_URL="http://127.0.0.1:8765/mcp"
MCP_URL="${CC_JUKEBOX_MCP_URL:-$DEFAULT_MCP_URL}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --relay-socket)
      [ "$#" -ge 2 ] || { echo "--relay-socket requires a value" >&2; exit 2; }
      RELAY_SOCKET="$2"
      shift 2
      ;;
    --relay-url)
      [ "$#" -ge 2 ] || { echo "--relay-url requires a value" >&2; exit 2; }
      RELAY_URL="$2"
      shift 2
      ;;
    --mcp-url)
      [ "$#" -ge 2 ] || { echo "--mcp-url requires a value" >&2; exit 2; }
      MCP_URL="$2"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./install.sh [--relay-socket PATH | --relay-url URL] [--mcp-url URL]

Options:
  --relay-socket PATH  Configure Claude Code statusline/hooks to use a remote
                       relay agent request socket, usually
                       ~/.cc-jukebox/run/agent-request.sock.
  --relay-url URL      Configure Claude Code statusline/hooks to use a local
                       HTTP relay URL, usually http://127.0.0.1:8765.
  --mcp-url URL        Configure Claude Code to connect to cc-jukebox as an
                       HTTP MCP server, usually http://127.0.0.1:8765/mcp.
EOF
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      exit 2
      ;;
  esac
done

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "\033[32m✓\033[0m %s\n" "$1"; }
warn() { printf "\033[33m!\033[0m %s\n" "$1"; }
die()  { printf "\033[31m✗ %s\033[0m\n" "$1" >&2; exit 1; }

bold "CC-Jukebox installer"
echo "  repo:    $REPO"
echo "  venv:    $HOME/.cc-jukebox/venv"
echo "  bin:     $HOME/.local/bin/cc-jukebox"
echo "  command: $HOME/.claude/commands/juke.md"
if [ -n "$RELAY_SOCKET" ]; then
  echo "  relay:   socket $RELAY_SOCKET"
elif [ -n "$RELAY_URL" ]; then
  echo "  relay:   url $RELAY_URL"
fi
if [ -n "$MCP_URL" ]; then
  echo "  mcp:     url $MCP_URL"
fi

# 1. find a Python ≥3.10
#    Honours $CC_JUKEBOX_PYTHON if set; otherwise scans PATH, Homebrew prefixes
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
if [ -n "${CC_JUKEBOX_PYTHON:-}" ] && check_py "$CC_JUKEBOX_PYTHON"; then
  PY="$CC_JUKEBOX_PYTHON"
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
      die "need curl to bootstrap uv. Install curl and re-run (or set CC_JUKEBOX_PYTHON=...)."
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

# 2. venv at ~/.cc-jukebox/venv
VENV="$HOME/.cc-jukebox/venv"
mkdir -p "$HOME/.cc-jukebox"
if [ -n "$MCP_URL" ]; then
  printf "%s\n" "$MCP_URL" > "$HOME/.cc-jukebox/mcp-url"
  ok "saved MCP URL for CLI commands: $HOME/.cc-jukebox/mcp-url"
fi
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
  if grep -q ">>> cc-jukebox >>>" "$rc"; then
    return 0  # already there
  fi
  {
    echo ""
    echo "# >>> cc-jukebox >>>"
    echo '# Added by cc-jukebox install.sh. Remove this block (or run uninstall.sh) to revert.'
    echo 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH";; esac'
    echo "# <<< cc-jukebox <<<"
  } >> "$rc"
  ok "added PATH block to $rc"
}
# create ~/.zshrc if missing (macOS default shell is zsh) so PATH actually gets set
[ -f "$HOME/.zshrc" ] || { touch "$HOME/.zshrc"; ok "created empty ~/.zshrc"; }
inject_path "$HOME/.zshrc"
inject_path "$HOME/.bashrc"

case ":$PATH:" in
  *":$BIN_DIR:"*) ok "$BIN_DIR is on PATH in this shell" ;;
  *) warn "Open a new terminal (or 'source ~/.zshrc') so cc-jukebox is on PATH." ;;
esac

# 5. install the /juke slash command (symlink so repo is source of truth)
CMD_DIR="$HOME/.claude/commands"
mkdir -p "$CMD_DIR"
CMD_LINK="$CMD_DIR/juke.md"
CMD_SRC="$REPO/commands/juke.md"
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

SETTINGS_ARGS=(
  --settings "$SETTINGS_FILE"
  --python "$VENV_PY"
  --repo "$REPO"
)
[ -z "$RELAY_SOCKET" ] || SETTINGS_ARGS+=(--relay-socket "$RELAY_SOCKET")
[ -z "$RELAY_URL" ] || SETTINGS_ARGS+=(--relay-url "$RELAY_URL")
[ -z "$MCP_URL" ] || SETTINGS_ARGS+=(--mcp-url "$MCP_URL")
"$VENV_PY" "$REPO/scripts/install_settings.py" "${SETTINGS_ARGS[@]}"

ok "Claude Code settings patched: $SETTINGS_FILE"

start_mcp_service() {
  [ -n "$MCP_URL" ] || return 0
  if [ "$(uname -s)" != "Darwin" ]; then
    warn "HTTP MCP configured at $MCP_URL. Auto-start is macOS-only; make sure the Mac-side server is reachable."
    return 0
  fi

  local parts host port path
  parts="$("$VENV_PY" - "$MCP_URL" <<'PY'
import sys
from urllib.parse import urlparse

url = sys.argv[1]
parsed = urlparse(url)
if parsed.scheme not in ("http", "https"):
    raise SystemExit(f"unsupported MCP URL scheme: {parsed.scheme or '(missing)'}")
host = parsed.hostname or "127.0.0.1"
port = parsed.port or (443 if parsed.scheme == "https" else 80)
path = parsed.path or "/mcp"
print(f"{host}\t{port}\t{path}")
PY
)"
  host="$(printf "%s" "$parts" | cut -f1)"
  port="$(printf "%s" "$parts" | cut -f2)"
  path="$(printf "%s" "$parts" | cut -f3)"

  case "$host" in
    127.0.0.1|localhost|::1) ;;
    *)
      warn "HTTP MCP URL is not localhost ($MCP_URL); not starting a local LaunchAgent."
      return 0
      ;;
  esac

  local label="com.cc-jukebox.server"
  local plist="$HOME/Library/LaunchAgents/$label.plist"
  local old_label="com.cc-jukebox.mcp-http"
  local old_plist="$HOME/Library/LaunchAgents/$old_label.plist"
  local log_dir="$HOME/.cc-jukebox/logs"
  mkdir -p "$(dirname "$plist")" "$log_dir"

  "$VENV_PY" - "$plist" "$TARGET" "$host" "$port" "$path" "$log_dir" <<'PY'
import plistlib
import sys
from pathlib import Path

plist, program, host, port, path, log_dir = sys.argv[1:]
data = {
    "Label": "com.cc-jukebox.server",
    "ProgramArguments": [
        program,
        "server",
        "--host",
        host,
        "--port",
        str(port),
        "--path",
        path,
    ],
    "RunAtLoad": True,
    "KeepAlive": True,
    "StandardOutPath": str(Path(log_dir) / "server.log"),
    "StandardErrorPath": str(Path(log_dir) / "server.err.log"),
    "EnvironmentVariables": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    },
}
with open(plist, "wb") as f:
    plistlib.dump(data, f)
PY

  local domain="gui/$(id -u)"
  launchctl bootout "$domain" "$old_plist" >/dev/null 2>&1 || true
  rm -f "$old_plist"
  launchctl bootout "$domain" "$plist" >/dev/null 2>&1 || true
  if launchctl bootstrap "$domain" "$plist" >/dev/null 2>&1; then
    launchctl kickstart -k "$domain/$label" >/dev/null 2>&1 || true
    if "$VENV_PY" - "$host" "$port" <<'PY'
import socket
import sys
import time

host, port = sys.argv[1], int(sys.argv[2])
for _ in range(40):
    try:
        with socket.create_connection((host, port), timeout=0.2):
            raise SystemExit(0)
    except OSError:
        time.sleep(0.1)
raise SystemExit(1)
PY
    then
      ok "HTTP MCP LaunchAgent started: $MCP_URL"
      ok "MCP logs: $log_dir/server.log"
    else
      warn "LaunchAgent loaded, but HTTP MCP is not listening at $MCP_URL."
      warn "Check logs: $log_dir/server.err.log"
    fi
  else
    warn "Could not start LaunchAgent. Run manually: cc-jukebox server --host $host --port $port --path $path"
  fi
}

start_mcp_service

# 7. Make sure data dir exists
"$VENV_PY" -c "from cc_jukebox.config import ensure_dirs; ensure_dirs()"
ok "data dir ready: ~/.cc-jukebox/"

echo
"$VENV/bin/cc-jukebox" welcome 2>/dev/null || true
echo
bold "From a new shell (or after 'source ~/.zshrc'):"
if [ -n "$MCP_URL" ]; then
  echo "  # MCP endpoint configured at $MCP_URL"
  echo "  cc-jukebox server      — manually run the HTTP MCP server for debugging"
fi
echo "  cc-jukebox player       — open the pixel player"
echo "  cc-jukebox watch        — live TUI"
echo "  /juke play 周杰伦        — drive it from Claude Code"
echo
warn "To remove: ./uninstall.sh   (add --purge to also delete ~/.cc-jukebox)"
