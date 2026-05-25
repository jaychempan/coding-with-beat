#!/usr/bin/env bash
# coding-with-beat — Codex CLI installer
# One-click, proxy-aware, idempotent. Re-running is safe.
#
# Steps:
#   1. Python ≥3.10 → shared venv at ~/.coding-with-beat/venv
#   2. coding-with-beat installed (editable) + cwb symlinked to ~/.local/bin/
#   3. Proxy normalised: detect system proxy → set both upper/lowercase +
#      NO_PROXY=127.0.0.1,localhost (so Codex reaches chatgpt.com AND local MCP)
#   4. Codex CLI installed / verified via npm
#   5. ~/.codex/config.toml (MCP) + ~/.codex/hooks.json (hooks) patched
#   6. cwb skill installed to ~/.codex/skills/cwb/
#   7. Music routing rules injected into ~/.codex/AGENTS.md
#   8. MCP server LaunchAgent started (macOS)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_MCP_URL="http://127.0.0.1:8765/mcp"
MCP_URL="${CWB_MCP_URL:-${CC_JUKEBOX_MCP_URL:-$DEFAULT_MCP_URL}}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mcp-url) [ "$#" -ge 2 ] || { echo "--mcp-url requires a value" >&2; exit 2; }
               MCP_URL="$2"; shift 2 ;;
    -h|--help) cat <<'EOF'
Usage: ./install_codex.sh [--mcp-url URL]
  --mcp-url URL   MCP server URL (default: http://127.0.0.1:8765/mcp)
EOF
      exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

bold() { printf "\033[1m%s\033[0m\n" "$1"; }
ok()   { printf "\033[32m✓\033[0m %s\n" "$1"; }
info() { printf "\033[34m·\033[0m %s\n" "$1"; }
warn() { printf "\033[33m!\033[0m %s\n" "$1"; }
die()  { printf "\033[31m✗ %s\033[0m\n" "$1" >&2; exit 1; }

bold "coding-with-beat — Codex CLI installer"

# ─────────────────────────────────────────────────────────────────────────────
# 1. Find Python ≥3.10
# ─────────────────────────────────────────────────────────────────────────────
check_py() {
  local cand="$1"
  [ -z "$cand" ] && return 1
  command -v "$cand" >/dev/null 2>&1 || [ -x "$cand" ] || return 1
  local v
  v="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || true)"
  case "$v" in 3.1[0-9]|3.[2-9][0-9]) return 0 ;; *) return 1 ;; esac
}

PY=""
[ -n "${CWB_PYTHON:-}" ] && check_py "$CWB_PYTHON" && PY="$CWB_PYTHON"
if [ -z "$PY" ]; then
  for cand in python3.13 python3.12 python3.11 python3.10 python3; do
    if check_py "$cand"; then PY="$(command -v "$cand")"; break; fi
  done
fi
if [ -z "$PY" ]; then
  for cand in /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 \
              /opt/homebrew/bin/python3.11 /opt/homebrew/bin/python3.10 \
              /usr/local/bin/python3.13   /usr/local/bin/python3.12 \
              /usr/local/bin/python3.11   /usr/local/bin/python3.10; do
    if check_py "$cand"; then PY="$cand"; break; fi
  done
fi

bootstrap_via_uv() {
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    command -v curl >/dev/null 2>&1 || die "need curl to bootstrap uv"
    curl -LsSf https://astral.sh/uv/install.sh | sh
  fi
  command -v uv >/dev/null 2>&1 || die "uv install failed"
  local found; found="$(uv python find 3.12 2>/dev/null || true)"
  if [ -z "$found" ] || [ ! -x "$found" ]; then uv python install 3.12; found="$(uv python find 3.12)"; fi
  if [ -z "$found" ] || [ ! -x "$found" ]; then die "uv python install failed"; fi
  PY="$found"
}

[ -n "$PY" ] || { warn "No Python ≥3.10 found — bootstrapping via uv"; bootstrap_via_uv; }
ok "python: $PY ($($PY --version))"

# ─────────────────────────────────────────────────────────────────────────────
# 2. Shared venv + coding-with-beat install
# ─────────────────────────────────────────────────────────────────────────────
VENV="$HOME/.coding-with-beat/venv"
mkdir -p "$HOME/.coding-with-beat"
printf "%s\n" "$REPO"    > "$HOME/.coding-with-beat/repo-path"
printf "%s\n" "$MCP_URL" > "$HOME/.coding-with-beat/mcp-url"

if [ -d "$VENV" ] && { [ ! -x "$VENV/bin/python" ] || [ ! -x "$VENV/bin/pip" ]; }; then
  warn "incomplete venv — recreating"; rm -rf "$VENV"
fi
if [ ! -d "$VENV" ]; then
  "$PY" -m venv "$VENV" || { bootstrap_via_uv; "$PY" -m venv "$VENV" || die "venv creation failed"; }
  ok "created venv at $VENV"
else
  ok "venv exists at $VENV"
fi

VENV_PY="$VENV/bin/python"
if [ -x "$VENV/bin/cwb" ]; then
  ok "coding-with-beat already installed — skipping pip"
else
  "$VENV_PY" -m pip install --quiet --upgrade pip
  "$VENV_PY" -m pip install --quiet -e "$REPO"
  ok "coding-with-beat installed"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. Symlink cwb to ~/.local/bin/
# ─────────────────────────────────────────────────────────────────────────────
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
TARGET="$VENV/bin/cwb"
LINK="$BIN_DIR/cwb"
[ -x "$TARGET" ] || die "expected $TARGET to exist after install"
if [ "$(readlink "$LINK" 2>/dev/null)" = "$TARGET" ]; then
  ok "cwb already linked"
elif [ -L "$LINK" ] || [ ! -e "$LINK" ]; then
  ln -sfn "$TARGET" "$LINK"
  ok "linked cwb -> $TARGET"
fi

inject_path() {
  local rc="$1"; [ -f "$rc" ] || return 0
  grep -q ">>> coding-with-beat >>>" "$rc" && return 0
  { echo ""; echo "# >>> coding-with-beat >>>";
    # shellcheck disable=SC2016
    echo 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH";; esac';
    echo "# <<< coding-with-beat <<<"; } >> "$rc"
  ok "PATH block added to $rc"
}
[ -f "$HOME/.zshrc" ] || touch "$HOME/.zshrc"
inject_path "$HOME/.zshrc"; inject_path "$HOME/.bashrc"

# ─────────────────────────────────────────────────────────────────────────────
# 4. Proxy normalisation
#    Detect the first proxy URL found in env → write both upper/lowercase +
#    NO_PROXY=127.0.0.1,localhost into shell profiles.
#    Codex (Rust) uses uppercase; curl/npm use lowercase.
#    NO_PROXY ensures the local MCP server is always reached directly.
# ─────────────────────────────────────────────────────────────────────────────
detect_proxy() {
  # macOS system proxy via scutil (works even before shell vars are set)
  local scutil_https="" scutil_http=""
  if command -v scutil >/dev/null 2>&1; then
    scutil_https="$(scutil --proxy 2>/dev/null | awk '/HTTPSProxy/{p=$3} /HTTPSPort/{port=$3} END{if(p) print "http://"p":"port}')"
    scutil_http="$(scutil --proxy 2>/dev/null | awk '/HTTPProxy /{p=$3} /HTTPPort /{port=$3} END{if(p) print "http://"p":"port}')"
  fi
  # env vars override system settings
  for var in HTTPS_PROXY https_proxy HTTP_PROXY http_proxy; do
    local val="${!var:-}"
    if [ -n "$val" ]; then echo "$val"; return; fi
  done
  [ -n "$scutil_https" ] && { echo "$scutil_https"; return; }
  [ -n "$scutil_http"  ] && { echo "$scutil_http";  return; }
}

PROXY_URL="$(detect_proxy || true)"

_NO_PROXY_BASE="127.0.0.1,localhost,::1"

inject_proxy_env() {
  local rc="$1" proxy="$2"
  [ -f "$rc" ] || return 0
  # Remove our old proxy block if present (handles port changes on re-run)
  "$PY" - "$rc" <<'PY'
import sys; path = sys.argv[1]
lines = open(path).readlines()
out, skip = [], False
for line in lines:
    if ">>> coding-with-beat proxy >>>" in line: skip = True
    if not skip: out.append(line)
    if "<<< coding-with-beat proxy <<<" in line: skip = False
open(path, "w").writelines(out)
PY
  {
    echo ""
    echo "# >>> coding-with-beat proxy >>>"
    echo "# Set by coding-with-beat install_codex.sh — edit here to change."
    if [ -n "$proxy" ]; then
      echo "export HTTP_PROXY=$proxy"
      echo "export HTTPS_PROXY=$proxy"
      echo "export http_proxy=$proxy"
      echo "export https_proxy=$proxy"
    fi
    # Always add NO_PROXY so local MCP server bypasses the proxy
    echo "export NO_PROXY=$_NO_PROXY_BASE"
    echo "export no_proxy=$_NO_PROXY_BASE"
    echo "# <<< coding-with-beat proxy <<<"
  } >> "$rc"
}

if [ -n "$PROXY_URL" ]; then
  inject_proxy_env "$HOME/.zshrc"  "$PROXY_URL"
  inject_proxy_env "$HOME/.bashrc" "$PROXY_URL"
  # Apply to current shell session too
  export HTTP_PROXY="$PROXY_URL" HTTPS_PROXY="$PROXY_URL"
  export http_proxy="$PROXY_URL" https_proxy="$PROXY_URL"
  ok "proxy normalised: $PROXY_URL (upper+lowercase, NO_PROXY=127.0.0.1,localhost)"
else
  # Still inject NO_PROXY even without a proxy (future-proofs if user adds one)
  inject_proxy_env "$HOME/.zshrc"  ""
  inject_proxy_env "$HOME/.bashrc" ""
  info "no proxy detected — NO_PROXY=127.0.0.1,localhost written anyway"
fi
export NO_PROXY="$_NO_PROXY_BASE" no_proxy="$_NO_PROXY_BASE"

# ─────────────────────────────────────────────────────────────────────────────
# 5. Codex CLI — install or verify
# ─────────────────────────────────────────────────────────────────────────────
install_codex_cli() {
  if command -v codex >/dev/null 2>&1; then
    ok "codex already installed: $(codex --version 2>/dev/null || echo '(unknown version)')"
    return 0
  fi
  if ! command -v npm >/dev/null 2>&1; then
    warn "npm not found — skipping Codex CLI install. Install Node.js then run: npm install -g @openai/codex"
    return 0
  fi

  info "Installing Codex CLI via npm..."
  local npm_args=()
  [ -n "$PROXY_URL" ] && npm_args+=(--proxy "$PROXY_URL" --https-proxy "$PROXY_URL")

  if npm install -g @openai/codex "${npm_args[@]}"; then
    ok "Codex CLI installed: $(codex --version 2>/dev/null || echo 'ok')"
  else
    warn "npm install failed. Try manually: npm install -g @openai/codex --proxy $PROXY_URL"
  fi
}
install_codex_cli

# ─────────────────────────────────────────────────────────────────────────────
# 6. Patch ~/.codex/config.toml + hooks.json + install skill
# ─────────────────────────────────────────────────────────────────────────────
"$VENV_PY" "$REPO/scripts/install_codex_config.py" \
  --python  "$VENV_PY" \
  --repo    "$REPO" \
  --mcp-url "$MCP_URL"
ok "Codex config patched"

# ─────────────────────────────────────────────────────────────────────────────
# 7. AGENTS.md — inject music routing rules into ~/.codex/AGENTS.md
# ─────────────────────────────────────────────────────────────────────────────
inject_agents_md() {
  local agents="$HOME/.codex/AGENTS.md"
  # Strip existing block on re-run so rules stay up-to-date
  if [ -f "$agents" ] && grep -q ">>> coding-with-beat >>>" "$agents"; then
    "$PY" - "$agents" <<'PY'
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
  touch "$agents"
  cat >> "$agents" <<'AGENTS'

# >>> coding-with-beat >>>
# Music routing — added by coding-with-beat install_codex.sh (remove block or run uninstall_codex.sh to revert)

## Music requests — when to use smart_search vs play_song

Use `play_song(query)` only for **specific** song title / artist / album (e.g. "周杰伦 晴天", "Taylor Swift").
Use `smart_search(queries=[...])` for **everything else**: mood, vibe, scene, fuzzy artist requests, genre + modifier, era, activity.

Call `smart_search` **once** with 2–3 angle queries. Do NOT call it multiple times — each call overwrites the queue.
After showing results (numbered globally), ask the user to pick by number and call `play_number(N)`. Do NOT auto-play.

## Library-only search

When the user says "从资料库找"/"资料库里有没有"/"我已经有这首"/"in my library"/"library only":
1. Call `search(query)`.
2. Only show results where `source == "library"`.
3. If none found, ask: "资料库里没找到，要不要搜一下线上？" — do NOT auto-expand.

## Scene dispatch

| Scene | Trigger words | queries |
|---|---|---|
| 🎧 Lofi | lofi, 深夜, 写代码, chillhop | `["lofi hip hop late night coding chill", "lofi jazz rain study instrumental", "chillhop beats lo-fi bedroom producer"]` |
| 🧠 Focus | 专注, 心流, ambient, 无人声, flow state | `["deep focus ambient instrumental no vocals", "flow state drone minimal electronic", "study music concentration piano quiet"]` |
| 🔥 Hype | 充能, 运动, workout, hype, 跑步 | `["morning energy upbeat pop indie fresh", "workout motivation electronic dance", "hype rap trap energetic beats pump"]` |
| ☕ Jazz | 爵士, jazz, 咖啡馆, bossa nova | `["smooth jazz cafe background mellow", "jazz trio acoustic bossa nova guitar", "late night jazz piano bar cool relaxed"]` |
| 🌆 Synthwave | 赛博, synthwave, 电子, 夜驾 | `["synthwave retrowave night drive neon", "cyberpunk electronic dark ambient synth", "80s retro synth outrun vapor"]` |
| 🌅 Relax | 放松, 解压, 下班, unwind | `["relaxing downtempo chill evening unwind", "acoustic folk gentle calm soft", "nature ambient breeze afternoon easy listening"]` |
| 🎹 Classical | 古典, 钢琴, 弦乐, classical | `["classical piano solo nocturne gentle", "string quartet orchestral cinematic calm", "bach mozart ambient classical study"]` |
| 💙 Sad | 伤感, 失落, 难过, heartbreak | `["melancholy emotional piano sad indie", "heartbreak slow ballad rnb rainy", "sorrowful strings cinematic emotional"]` |
| 🎉 Party | 派对, party, edm, 蹦迪 | `["party dance pop upbeat celebratory", "edm festival club electronic banger", "latin pop reggaeton dance floor"]` |
| 🏮 Chinese | 国风, 华语, 民谣, 古风 | `["中国风 古风 古琴 传统乐器", "华语流行 国语歌 indie 民谣", "chinese traditional folk guzheng erhu instrumental"]` |
| 🌙 Sleep | 助眠, 失眠, sleep, 白噪音 | `["sleep music white noise ambient drone", "lullaby soft piano rain sleep calm", "meditation deep sleep binaural delta waves"]` |

## Fuzzy / artist-only requests → smart_search

When the user names an artist without a specific song (e.g. "来首周杰伦的", "林明浩最近流行的"):
`smart_search(queries=["{artist} 热门", "{artist} 新歌 2024", "{artist} 代表作"])`

When the user asks for something similar to an artist (e.g. "像Taylor Swift的"):
generate 3 queries based on that artist's known style.

## play_number — number parsing

Resolve before calling `play_number(N)`:
- "第一" / "1" / "one" / "the first" → play_number(1)
- "第二" / "2" / "second" → play_number(2)
- "第三首" / "第三个" / "三" / "3" → play_number(3)
- "最后一首" / "last one" → use the highest number shown in results

Chinese ordinals 第一/第二/第三/第四/第五 = 1/2/3/4/5.

## play_number recovery

If `play_number(N)` errors with "only"/"had"/"out of range": re-run the same `smart_search(queries=[...])` automatically, then call `play_number(N)` again. Do NOT ask the user to retry.
# <<< coding-with-beat <<<
AGENTS
  ok "music routing rules injected into $agents"
}
inject_agents_md

# ─────────────────────────────────────────────────────────────────────────────
# 8. MCP LaunchAgent (macOS)
# ─────────────────────────────────────────────────────────────────────────────
start_mcp_service() {
  [ "$(uname -s)" = "Darwin" ] || { warn "Auto-start is macOS-only."; return 0; }

  local parts host port path
  parts="$("$VENV_PY" - "$MCP_URL" <<'PY'
import sys
from urllib.parse import urlparse
u = urlparse(sys.argv[1])
if u.scheme not in ("http","https"): raise SystemExit("unsupported scheme")
print(f"{u.hostname or '127.0.0.1'}\t{u.port or 80}\t{u.path or '/mcp'}")
PY
)"
  host="$(printf "%s" "$parts" | cut -f1)"
  port="$(printf "%s" "$parts" | cut -f2)"
  path="$(printf "%s" "$parts" | cut -f3)"

  case "$host" in 127.0.0.1|localhost|::1) ;;
    *) warn "MCP URL is not localhost — skipping LaunchAgent"; return 0 ;;
  esac

  local label="com.coding-with-beat.server"
  local plist="$HOME/Library/LaunchAgents/$label.plist"
  local log_dir="$HOME/.coding-with-beat/logs"
  mkdir -p "$(dirname "$plist")" "$log_dir"

  "$VENV_PY" - "$plist" "$TARGET" "$host" "$port" "$path" "$log_dir" <<'PY'
import plistlib, sys
from pathlib import Path
plist, program, host, port, path, log_dir = sys.argv[1:]
data = {
    "Label": "com.coding-with-beat.server",
    "ProgramArguments": [program, "server", "--host", host, "--port", port, "--path", path],
    "RunAtLoad": True, "KeepAlive": True,
    "StandardOutPath": str(Path(log_dir)/"server.log"),
    "StandardErrorPath": str(Path(log_dir)/"server.err.log"),
    "EnvironmentVariables": {
        "PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
    },
}
with open(plist, "wb") as f: plistlib.dump(data, f)
PY

  local domain
  domain="gui/$(id -u)"
  # Always restart so newly installed code is picked up.
  launchctl bootout "$domain" "$plist" >/dev/null 2>&1 || true
  if launchctl bootstrap "$domain" "$plist" >/dev/null 2>&1; then
    launchctl kickstart -k "$domain/$label" >/dev/null 2>&1 || true
    if "$VENV_PY" - "$host" "$port" <<'PY'
import socket, sys, time
h, p = sys.argv[1], int(sys.argv[2])
for _ in range(40):
    try:
        with socket.create_connection((h,p), timeout=0.2): raise SystemExit(0)
    except OSError: time.sleep(0.1)
raise SystemExit(1)
PY
    then
      ok "MCP server running at $MCP_URL"
    else
      warn "LaunchAgent loaded but MCP not responding — check $log_dir/server.err.log"
    fi
  else
    warn "Could not start LaunchAgent. Run manually: cwb server --host $host --port $port --path $path"
  fi
}
start_mcp_service

# ─────────────────────────────────────────────────────────────────────────────
# Init data dir
# ─────────────────────────────────────────────────────────────────────────────
"$VENV_PY" -c "from coding_with_beat.config import ensure_dirs; ensure_dirs()"

echo
"$VENV/bin/cwb" welcome 2>/dev/null || true
echo
bold "Done! Open a new shell or run:  source ~/.zshrc"
echo
echo "  In Codex:  'play some lofi'  or  'cwb play lofi beats'"
echo "  CLI:       cwb watch / cwb player / cwb np"
[ -n "$PROXY_URL" ] && echo "  Proxy:     $PROXY_URL (both Codex → chatgpt.com and local MCP handled)"
echo
warn "To uninstall: ./uninstall_codex.sh"
