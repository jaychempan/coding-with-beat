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
#   5. Symlinks all cwb skills into ~/.claude/skills/.
#   6. Injects music intent routing rules into ~/.claude/CLAUDE.md.
#   7. Registers HTTP MCP server, statusline, vibe hooks, and the /cwb
#      UserPromptExpansion hook with Claude Code via ~/.claude/settings.json.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_MCP_URL="http://127.0.0.1:8765/mcp"
MCP_URL="${CWB_MCP_URL:-${CC_JUKEBOX_MCP_URL:-$DEFAULT_MCP_URL}}"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --mcp-url)
      [ "$#" -ge 2 ] || { echo "--mcp-url requires a value" >&2; exit 2; }
      MCP_URL="$2"
      shift 2
      ;;
    -h|--help)
      cat <<'EOF'
Usage: ./install.sh [--mcp-url URL]

Options:
  --mcp-url URL        Configure Claude Code to connect to coding-with-beat as an
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

bold "coding-with-beat installer"
echo "  repo:    $REPO"
echo "  venv:    $HOME/.coding-with-beat/venv"
echo "  bin:     $HOME/.local/bin/cwb"
echo "  command: $HOME/.claude/commands/cwb.md"
if [ -n "$MCP_URL" ]; then
  echo "  mcp:     url $MCP_URL"
fi

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
  if [ -z "$found" ] || [ ! -x "$found" ]; then die "uv python install failed."; fi
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
printf "%s\n" "$REPO" > "$HOME/.coding-with-beat/repo-path"
if [ -n "$MCP_URL" ]; then
  printf "%s\n" "$MCP_URL" > "$HOME/.coding-with-beat/mcp-url"
  ok "saved MCP URL for CLI commands: $HOME/.coding-with-beat/mcp-url"
fi
if [ -d "$VENV" ] && { [ ! -x "$VENV/bin/python" ] || [ ! -x "$VENV/bin/pip" ]; }; then
  warn "incomplete venv at $VENV — recreating it."
  rm -rf "$VENV"
fi
if [ ! -d "$VENV" ]; then
  if ! "$PY" -m venv "$VENV"; then
    warn "could not create venv with $PY; trying uv-managed Python."
    rm -rf "$VENV"
    bootstrap_via_uv
    "$PY" -m venv "$VENV" || die "could not create venv at $VENV"
  fi
  ok "created venv at $VENV"
else
  ok "venv exists at $VENV"
fi
VENV_PY="$VENV/bin/python"
_installed_loc=$("$VENV_PY" -m pip show coding-with-beat 2>/dev/null | grep "^Location:" | awk '{print $2}')
if [ "$_installed_loc" = "$REPO" ] && [ -x "$VENV/bin/cwb" ]; then
  ok "coding-with-beat already installed from $REPO — skipping pip"
else
  "$VENV_PY" -m pip install --quiet --upgrade pip
  "$VENV_PY" -m pip install --quiet -e "$REPO"
  ok "installed/updated coding-with-beat (editable) -> $REPO"
fi

# 3. symlink ~/.local/bin/cwb
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
LINK="$BIN_DIR/cwb"
TARGET="$VENV/bin/cwb"
[ -x "$TARGET" ] || die "expected $TARGET to exist after pip install; aborting."
if [ "$(readlink "$LINK" 2>/dev/null)" = "$TARGET" ]; then
  ok "cwb already linked"
elif [ -L "$LINK" ] || [ ! -e "$LINK" ]; then
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
    # shellcheck disable=SC2016
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

# 5. install all slash commands from commands/ (symlink so repo is source of truth)
CMD_DIR="$HOME/.claude/commands"
CMD_SRC_DIR="$REPO/commands"
mkdir -p "$CMD_DIR"
[ -d "$CMD_SRC_DIR" ] || die "missing $CMD_SRC_DIR — repo is incomplete."
for cmd_src in "$CMD_SRC_DIR"/*.md; do
  [ -f "$cmd_src" ] || continue
  cmd_name="$(basename "$cmd_src")"
  cmd_link="$CMD_DIR/$cmd_name"
  if [ -L "$cmd_link" ] || [ ! -e "$cmd_link" ]; then
    ln -sfn "$cmd_src" "$cmd_link"
    ok "command $cmd_name linked"
  else
    warn "command $cmd_name already exists as a regular file — leaving it alone."
  fi
done
# Remove stale command symlinks that point into our repo's commands dir
for cmd_link in "$CMD_DIR"/*.md; do
  [ -L "$cmd_link" ] || continue
  link_target="$(readlink "$cmd_link")"
  cmd_name="$(basename "$cmd_link")"
  case "$link_target" in
    "$CMD_SRC_DIR"/*)
      [ -f "$CMD_SRC_DIR/$cmd_name" ] || { rm "$cmd_link"; ok "removed stale command $cmd_name"; }
      ;;
  esac
done

# 6. install Claude Code skills (symlink so repo is source of truth)
SKILLS_SRC_DIR="$REPO/skills"
SKILLS_DST_DIR="$HOME/.claude/skills"
if [ -d "$SKILLS_SRC_DIR" ]; then
  mkdir -p "$SKILLS_DST_DIR"
  for skill_src in "$SKILLS_SRC_DIR"/*/; do
    skill_name="$(basename "$skill_src")"
    skill_dst="$SKILLS_DST_DIR/$skill_name"
    if [ -L "$skill_dst" ]; then
      ln -sfn "$skill_src" "$skill_dst"
      ok "skill $skill_name updated"
    elif [ ! -e "$skill_dst" ]; then
      ln -sfn "$skill_src" "$skill_dst"
      ok "skill $skill_name linked"
    else
      warn "skill $skill_name already exists as a non-symlink — leaving it alone."
    fi
  done
  # Remove stale skill symlinks that point into our repo's skills dir
  for skill_dst in "$SKILLS_DST_DIR"/*/; do
    skill_dst="${skill_dst%/}"
    [ -L "$skill_dst" ] || continue
    link_target="$(readlink "$skill_dst")"
    link_target="${link_target%/}"
    skill_name="$(basename "$skill_dst")"
    case "$link_target" in
      "$SKILLS_SRC_DIR"/*)
        [ -d "$SKILLS_SRC_DIR/$skill_name" ] || { rm "$skill_dst"; ok "removed stale skill $skill_name"; }
        ;;
    esac
  done
else
  warn "skills/ directory not found in repo — skipping skill installation."
fi

# 7. inject music intent routing rules into ~/.claude/CLAUDE.md (idempotent)
GLOBAL_CLAUDE_MD="$HOME/.claude/CLAUDE.md"
CWB_CLAUDE_BEGIN="# >>> coding-with-beat >>>"
CWB_CLAUDE_END="# <<< coding-with-beat <<<"
inject_claude_md() {
  # Remove any prior cwb block first (idempotent)
  if [ -f "$GLOBAL_CLAUDE_MD" ] && grep -q "$CWB_CLAUDE_BEGIN" "$GLOBAL_CLAUDE_MD"; then
    # Use awk to delete lines between markers (inclusive)
    awk "/$CWB_CLAUDE_BEGIN/{found=1} !found{print} /$CWB_CLAUDE_END/{found=0}" \
      "$GLOBAL_CLAUDE_MD" > "$GLOBAL_CLAUDE_MD.tmp" && mv "$GLOBAL_CLAUDE_MD.tmp" "$GLOBAL_CLAUDE_MD"
  fi
  cat >> "$GLOBAL_CLAUDE_MD" <<'CLAUDEMD'

# >>> coding-with-beat >>>
# Music intent routing — added by coding-with-beat install.sh (remove block or run uninstall.sh to revert)

## Music requests — when to use smart_search vs play_song

Use `play_song(query)` only for **specific** song title / artist / album (e.g. "周杰伦 晴天", "Taylor Swift").
Use `smart_search(queries=[...])` for **everything else**: mood, vibe, scene, fuzzy artist requests, genre + modifier, era, activity.

Call `smart_search` **once** with 2–3 angle queries. Do NOT call it multiple times — each call overwrites the queue.
After showing results (numbered globally), ask the user to pick by number and call `play_number(N)`. Do NOT auto-play.

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

Always resolve the user's expression to an integer before calling `play_number(N)`:
- "第一" / "1" / "one" / "the first" → play_number(1)
- "第二" / "2" / "second" → play_number(2)
- "第三首" / "第三个" / "三" / "3" → play_number(3)
- "最后一首" / "last one" → use the highest number shown in results

Chinese ordinals 第一/第二/第三/第四/第五 = 1/2/3/4/5. Always resolve before calling.

## play_number recovery

If `play_number(N)` errors with "only"/"had"/"out of range": re-run the same `smart_search(queries=[...])` automatically, then call `play_number(N)` again. Do NOT ask the user to retry.

## Loved / 喜欢列表

When user says: 从喜欢里 / 收藏里找 / 我喜欢的 / loved only / play from liked / 心动歌单
→ call `search_loved(query)` instead of `smart_search()`

When user says: 列出收藏 / 我的喜欢 / show liked / list loved / 喜欢列表
→ call `list_loved()`

Normal `smart_search()` already includes loved tracks (ranked first, tagged [♥ 喜欢]).
# <<< coding-with-beat <<<
CLAUDEMD
  ok "music routing rules written to $GLOBAL_CLAUDE_MD"
}
inject_claude_md

# 8. inject cwb-companion routing rules into ~/.claude/CLAUDE.md (idempotent)
COMPANION_BEGIN="# >>> cwb-companion >>>"
COMPANION_END="# <<< cwb-companion <<<"
inject_companion_claude_md() {
  if [ -f "$GLOBAL_CLAUDE_MD" ] && grep -q "$COMPANION_BEGIN" "$GLOBAL_CLAUDE_MD"; then
    awk "/$COMPANION_BEGIN/{found=1} !found{print} /$COMPANION_END/{found=0}" \
      "$GLOBAL_CLAUDE_MD" > "$GLOBAL_CLAUDE_MD.tmp" && mv "$GLOBAL_CLAUDE_MD.tmp" "$GLOBAL_CLAUDE_MD"
  fi
  cat >> "$GLOBAL_CLAUDE_MD" <<'COMPANIONMD'

# >>> cwb-companion >>>
# DJ Buddy companion mode — added by coding-with-beat install.sh

## Companion mode

When the `cwb-companion` skill is loaded, call `companion_check(trigger)`
proactively at these moments (the tool handles cooldown internally):

| Moment | trigger |
|--------|---------|
| First reply of a new session | `session_start` |
| 3+ consecutive test failures observed | `debug_struggle` |
| git commit success / tests all green | `victory` |
| 20+ tools used, no music in 25+ min | `idle_checkin` |
| User signals end of session | `session_end` |

If `companion_check` returns `(not needed right now)`, stay silent.
If it returns a card, output it in full (one short lead-in phrase is fine).
Wait for the user to pick a number, then call `play_number(N)`.
# <<< cwb-companion <<<
COMPANIONMD
  ok "cwb-companion rules written to $GLOBAL_CLAUDE_MD"
}
inject_companion_claude_md

# 9. patch ~/.claude/settings.json (hooks, statusLine) + register MCP via claude CLI
SETTINGS_DIR="$HOME/.claude"
SETTINGS_FILE="$SETTINGS_DIR/settings.json"
mkdir -p "$SETTINGS_DIR"

SETTINGS_ARGS=(
  --settings "$SETTINGS_FILE"
  --python "$VENV_PY"
  --repo "$REPO"
)
# Pass --mcp-url so install_settings.py can remove the stale mcpServers key if present
[ -z "$MCP_URL" ] || SETTINGS_ARGS+=(--mcp-url "$MCP_URL")
"$VENV_PY" "$REPO/scripts/install_settings.py" "${SETTINGS_ARGS[@]}"
ok "Claude Code settings patched: $SETTINGS_FILE"

# Register MCP server via `claude mcp add` (user scope = all directories).
# This writes to ~/.claude.json which is what Claude Code CLI actually reads.
if [ -n "$MCP_URL" ] && command -v claude >/dev/null 2>&1; then
  if claude mcp add --transport http --scope user coding-with-beat "$MCP_URL" >/dev/null 2>&1; then
    ok "MCP server registered (user scope): $MCP_URL"
  else
    warn "claude mcp add failed — run manually: claude mcp add --transport http --scope user coding-with-beat $MCP_URL"
  fi
fi

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

  local label="com.coding-with-beat.server"
  local plist="$HOME/Library/LaunchAgents/$label.plist"
  local old_label="com.cc-jukebox.mcp-http"
  local old_plist="$HOME/Library/LaunchAgents/$old_label.plist"
  local old_server_label="com.cc-jukebox.server"
  local old_server_plist="$HOME/Library/LaunchAgents/$old_server_label.plist"
  local log_dir="$HOME/.coding-with-beat/logs"
  mkdir -p "$(dirname "$plist")" "$log_dir"

  "$VENV_PY" - "$plist" "$TARGET" "$host" "$port" "$path" "$log_dir" <<'PY'
import plistlib
import sys
from pathlib import Path

plist, program, host, port, path, log_dir = sys.argv[1:]
data = {
    "Label": "com.coding-with-beat.server",
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

  local domain
  domain="gui/$(id -u)"
  # Clean up legacy plist names from older installs
  launchctl bootout "$domain" "$old_plist" >/dev/null 2>&1 || true
  rm -f "$old_plist"
  launchctl bootout "$domain" "$old_server_plist" >/dev/null 2>&1 || true
  rm -f "$old_server_plist"
  # Always restart so newly installed code is picked up.
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
    warn "Could not start LaunchAgent. Run manually: cwb server --host $host --port $port --path $path"
  fi
}

start_mcp_service

start_updater_service() {
  [ "$(uname -s)" = "Darwin" ] || return 0

  local label="com.coding-with-beat.updater"
  local plist="$HOME/Library/LaunchAgents/$label.plist"
  local log_dir="$HOME/.coding-with-beat/logs"
  local updater="$HOME/.coding-with-beat/updater.sh"


  # Write the updater shell script
  cat > "$updater" <<UPDATER
#!/usr/bin/env bash
# Auto-generated by coding-with-beat install.sh — do not edit.
SRC="$REPO"
[ -d "\$SRC/.git" ] || exit 0
git -C "\$SRC" checkout -- '*.egg-info/' 2>/dev/null || true
OUT=\$(git -C "\$SRC" pull --ff-only 2>&1)
echo "\$(date '+%Y-%m-%d %H:%M:%S') \$OUT"
if echo "\$OUT" | grep -qv "Already up to date"; then
  # New commits landed — reinstall and restart the MCP server
  "$VENV/bin/pip" install -q -e "\$SRC"
  launchctl kickstart -k "gui/\$(id -u)/com.coding-with-beat.server" >/dev/null 2>&1 || true
  echo "\$(date '+%Y-%m-%d %H:%M:%S') restarted coding-with-beat server"
fi
UPDATER
  chmod +x "$updater"

  # Write the plist (runs daily at 03:00)
  "$VENV_PY" - "$plist" "$updater" "$log_dir" <<'PY'
import plistlib, sys
from pathlib import Path
plist, script, log_dir = sys.argv[1:]
data = {
    "Label": "com.coding-with-beat.updater",
    "ProgramArguments": ["/bin/bash", script],
    "StartCalendarInterval": {"Hour": 3, "Minute": 0},
    "StandardOutPath": str(Path(log_dir) / "updater.log"),
    "StandardErrorPath": str(Path(log_dir) / "updater.log"),
    "RunAtLoad": False,
}
with open(plist, "wb") as f:
    plistlib.dump(data, f)
PY

  local domain
  domain="gui/$(id -u)"
  launchctl bootout "$domain" "$plist" >/dev/null 2>&1 || true
  if launchctl bootstrap "$domain" "$plist" >/dev/null 2>&1; then
    ok "Auto-updater registered (daily at 03:00)"
  else
    warn "Could not register auto-updater LaunchAgent"
  fi
}

start_updater_service

# 9. Make sure data dir exists
"$VENV_PY" -c "from coding_with_beat.config import ensure_dirs; ensure_dirs()"
ok "data dir ready: ~/.coding-with-beat/"

bold "From a new shell (or after 'source ~/.zshrc'):"
if [ -n "$MCP_URL" ]; then
  echo "  # MCP endpoint configured at $MCP_URL"
  echo "  cwb server      — manually run the HTTP MCP server for debugging"
fi
echo "  cwb player       — open the pixel player"
echo "  cwb watch        — live TUI"
echo "  /cwb play lofi beats   — drive it from Claude Code"
echo
warn "To remove: ./uninstall.sh   (add --purge to also delete ~/.coding-with-beat)"
echo
PYTHONUTF8=1 "$VENV_PY" -c "from coding_with_beat.ui.frame import welcome_screen; print(welcome_screen())" || true
