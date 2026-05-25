# Coding with Beat — Codex CLI Integration

![Codex CLI](https://img.shields.io/badge/Codex_CLI-compatible-10a37f?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-28_tools-7c5cbf?style=flat-square)
![Platform](https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)

A complete guide to running coding-with-beat with **OpenAI Codex CLI** (`@openai/codex`).

[← Back to main README](README.md)

---

## What you get

| Feature | Codex CLI | Claude Code |
|---------|-----------|-------------|
| MCP music tools (28 tools) | ✓ | ✓ |
| Vibe engine (mood tracking) | ✓ | ✓ |
| Hook events: PreToolUse / PostToolUse | ✓ | ✓ |
| Hook events: SessionStart / Stop | ✓ | ✓ |
| Hook event: UserPromptSubmit (`cwb …`) | ✓ | ✓ (UserPromptExpansion) |
| Mood notifications via systemMessage | ✓ | — |
| SubagentStart / SubagentStop reactions | ✓ (Codex-only) | — |
| PermissionRequest pause tracking | ✓ (Codex-only) | — |
| Persistent statusline | tmux / Neovim | native statusLine.command |
| `/cwb` slash commands | via `cwb ` prefix | ✓ |
| Auto-play on session start | ✓ | ✓ |
| Proxy-aware install | ✓ | — |

---

## Installation

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap_codex.sh | sh
```

Or manually:

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install_codex.sh
```

The installer does everything in order, skipping steps that are already complete:

1. **Finds Python ≥3.10** — tries system Python, falls back to bootstrapping `uv` + Python 3.12
2. **Creates a shared venv** at `~/.coding-with-beat/venv` and installs coding-with-beat (editable)
3. **Symlinks `cwb`** to `~/.local/bin/cwb` and injects a PATH block into `~/.zshrc` / `~/.bashrc`
4. **Normalises proxy settings** — detects system proxy, writes both upper/lowercase `HTTP_PROXY` / `HTTPS_PROXY` plus `NO_PROXY=127.0.0.1,localhost` (see [Proxy](#proxy) below)
5. **Installs Codex CLI** via `npm install -g @openai/codex` if not already present
6. **Patches `~/.codex/config.toml`** with the MCP server endpoint
7. **Patches `~/.codex/hooks.json`** with all hook registrations (idempotent; tagged `_owner = "coding-with-beat"`)
8. **Installs the `cwb` skill** to `~/.codex/skills/cwb/SKILL.md`
9. **Starts the MCP LaunchAgent** (macOS) — runs `cwb server` in the background and waits for it to respond

Open a new shell and start a Codex session. The `cwb` skill activates automatically when you mention music.

### Optional: remote MCP server

```bash
./install_codex.sh --mcp-url http://127.0.0.1:8765/mcp
```

Use this when the MCP server runs on another machine (e.g. via SSH reverse tunnel). See [SSH Remote](#ssh-remote) below.

### Uninstall

```bash
./uninstall_codex.sh           # remove Codex config, skill, LaunchAgent
./uninstall_codex.sh --purge   # same + delete ~/.coding-with-beat/
```

---

## Proxy

Codex CLI is written in Rust and reads **uppercase** `HTTPS_PROXY`. `npm` and `curl` read lowercase. The installer writes both:

```bash
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
export http_proxy=http://your-proxy:port
export https_proxy=http://your-proxy:port
export NO_PROXY=127.0.0.1,localhost,::1
export no_proxy=127.0.0.1,localhost,::1
```

`NO_PROXY` is critical: it keeps Codex from routing the local MCP server (`127.0.0.1:8765`) through the proxy.

The installer detects your proxy from environment variables first, then from macOS `scutil --proxy`. If you re-run the installer after changing your proxy URL, the old block is replaced automatically.

---

## How hooks work

Hooks fire on every event and route to `coding_with_beat/codex_vibe.py` via:

```
~/.coding-with-beat/venv/bin/python -m coding_with_beat codex_hook
```

### PreToolUse / PostToolUse — vibe engine

Every tool call goes through the vibe engine. It reads the tool name and input, classifies the event into a (mood, vibe) pair, and updates `~/.coding-with-beat/state.json`.

Example mood shifts:

| Event | Mood | Vibe |
|-------|------|------|
| `git commit` (Bash) | `victory` | `victory` |
| `git push` (Bash) | `happy` | `victory` |
| Test runner succeeds | `victory` | `victory` |
| Test runner fails | `sad` | `fail` |
| File edit / write | `focus` | `build` |
| Editing test files | `focus` | `debug` |
| Reading / searching files | `thinking` | `review` |
| Session start | `happy` | `focus` |
| Session stop | `sleep` | `idle` |

When a significant mood change occurs (victory / panic / sad), Codex shows a **DJ Buddy notification** as a `systemMessage`:

```
🎉 DJ Buddy: "Ship it!" [commit]
😱 DJ Buddy: "Don't panic. Breathe." [debug]
💔 DJ Buddy: "It happens to everyone." [sad]
```

### SessionStart — music context injection

When a new Codex session starts, if music is playing the hook injects:

```
🎵 coding-with-beat active. Now playing: Midnight City — M83.
```

This appears as a system message so Codex "knows" what's playing from the start of the conversation.

### UserPromptSubmit — cwb command routing

When you type `cwb play lofi` or `/cwb next`, the hook intercepts it before Codex processes it.

**Routing strategy:**

| Command type | Examples | Handler |
|--------------|----------|---------|
| Action | `play`, `pause`, `next`, `prev`, `like`, `volume`, `seek`, `mode` | Hook → executes `cwb` CLI → brief `stopReason` |
| Display | `list`, `search`, `np`, `status`, `history`, `lyrics`, `player`, `help` | Passes through → Codex uses MCP tools → formatted output |

Display commands are passed through because Codex can render multi-line MCP output properly, whereas `stopReason` is a single notification line.

### SubagentStart / SubagentStop (Codex-only)

When Codex spawns a subagent for multi-step tasks, DJ Buddy reacts:

```
🤖 DJ Buddy: "In the zone." (subagent online)
```

SubagentStop is tracked silently for state.

### PermissionRequest (Codex-only)

When Codex pauses to ask for permission to run a tool, the mood shifts to `neutral` — reflecting the "waiting" state in the vibe engine.

---

## Using music commands

### Natural language (recommended)

The `cwb` skill is loaded automatically. Just talk to Codex:

```
play some lofi
skip this track
what's playing
pause the music
volume 60
```

### `cwb ` prefix

Codex doesn't support custom slash commands, but the hook intercepts the `cwb ` prefix:

```
cwb play "lofi beats"
cwb next
cwb pause
cwb volume 70
cwb like
```

### Display commands — let Codex handle them

For commands that show multi-line output, skip the prefix and ask naturally, or use the prefix (it passes through to MCP):

```
cwb list                # lists library tracks via MCP
cwb np                  # now playing via MCP
cwb search "jazz"       # search via MCP
cwb status              # full status via MCP
cwb history             # recently played tracks
cwb player              # pixel player panel
cwb lyrics              # lyrics window
```

Or just ask: `what's playing?` `show me the library` `search for jazz`.

### `cwb watch` / `cwb karaoke` — run directly in terminal

These open interactive TUI sessions; run them directly in your shell, not via Codex:

```bash
cwb watch       # live player TUI (q to quit)
cwb karaoke     # full-screen karaoke (q to quit)
```

| Key | Action |
|-----|--------|
| `Space` | Play / pause |
| `n` | Next |
| `p` | Previous |
| `l` | Like |
| `0-9` | Type a track number + `Enter` to jump to it |
| `q` | Quit |

### Project auto-play

Add a `.coding-with-beat.toml` to your project root:

```toml
auto_play_on_session = true
default_query = "lofi beats"
```

When Codex starts in that directory, it automatically plays the query.

---

## Statusline (alternatives)

Codex CLI has no native `statusLine.command` like Claude Code. Two alternatives:

### tmux status-right

```tmux
set -g status-right-length 180
set -g status-interval 1
set -g status-right '#(printf "{\"columns\":170}" | cwb statusline | perl -pe "s/\e\[[0-9;]*m//g")'
```

The output:

```
(•_•) ⚡  ▶ Midnight City — M83  ██████░░░░░░░░  [build]  ▃▆█▆▃  │ ♪ lyric preview
```

`perl` strips ANSI codes because tmux uses its own styling syntax.

### Neovim statusline

```lua
local cwb = { text = "", running = false }

local function strip_ansi(text)
  return text:gsub("\27%[[0-9;]*m", "")
end

local function refresh()
  if cwb.running or vim.fn.executable("cwb") == 0 then return end
  cwb.running = true
  vim.system({ "cwb", "statusline" }, {
    text = true,
    stdin = vim.json.encode({ columns = 90 }),
  }, function(result)
    vim.schedule(function()
      cwb.running = false
      if result.code == 0 and result.stdout then
        cwb.text = vim.trim(strip_ansi(result.stdout)):gsub("%%", "%%%%")
        vim.cmd.redrawstatus()
      end
    end)
  end)
end

_G.cwb = cwb
vim.fn.timer_start(1000, refresh, { ["repeat"] = -1 })
refresh()
vim.o.statusline = "%f %m%r %= %{v:lua.cwb.text}"
```

### Standalone statusline renderer

`cwb statusline` reads optional JSON from stdin and prints one compact line:

```bash
printf '{"columns":120}' | cwb statusline
```

---

## SSH Remote

If Codex runs on a server and Apple Music is on your Mac:

```bash
# Local Mac: start the MCP server
./install_codex.sh

# Local Mac: forward it to the server
ssh -N -R 127.0.0.1:8765:127.0.0.1:8765 user@server

# Server: install and point at the forwarded endpoint
./install_codex.sh --mcp-url http://127.0.0.1:8765/mcp
```

As long as the SSH tunnel is active, all Codex sessions on the server control the Mac-side music.

---

## Debugging

```bash
# Check if MCP server is running
nc -z 127.0.0.1 8765 && echo "MCP port is listening"

# Start manually
cwb server --host 127.0.0.1 --port 8765 --path /mcp

# Check LaunchAgent logs
tail -f ~/.coding-with-beat/logs/server.err.log

# Test the hook directly
echo '{"hook_event_name":"SessionStart"}' | \
  ~/.coding-with-beat/venv/bin/python -m coding_with_beat codex_hook

# Disable the hook temporarily
CWB_DISABLE_HOOK=1 codex
```

### Common issues

**MCP connection refused in Codex**
- Check `NO_PROXY` includes `127.0.0.1,localhost`. Without it, Codex routes localhost through the proxy.
- Verify the LaunchAgent is running: `launchctl list | grep coding-with-beat`

**Codex can't reach chatgpt.com**
- Check that `HTTPS_PROXY` (uppercase) is set. Codex reads uppercase only.
- Run `env | grep -i proxy` in a new shell after sourcing `~/.zshrc`.

**Hook not firing**
- Check `~/.codex/hooks.json` contains your hook entries.
- Re-run `./install_codex.sh` to re-patch.

**`cwb` not found**
- Run `source ~/.zshrc` or open a new shell.
- Check `~/.local/bin/cwb` exists and is executable.
