# Coding With Beat

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-c85f41?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-28_tools-7c5cbf?style=flat-square)
![Apple Music](https://img.shields.io/badge/Apple_Music-supported-FC3C44?style=flat-square)
![Version](https://img.shields.io/badge/version-0.1.0-9bbc0f?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
[![Website](https://img.shields.io/badge/website-codebeat.top-9bbc0f?style=flat-square)](https://codebeat.top)

> **When was the last time you sang and danced while vibecoding?**（上次 vibecoding 时又唱又跳是什么时候？）
>
> Right. You can't remember.（对，你已经不记得了。）

![](assets/welcome_log.png)

A pixel-art DJ companion that lives inside Claude Code. It plays music, shows lyrics, celebrates when you commit, and panics with you when tests fail.

[中文文档](README_CN.md) ／ [日本語](README_JP.md)

---

## Features

- **MCP server** — 28 tools so you can tell Claude "play some lofi", "skip this", "what's playing" and it just works.
- **Music sources** — Apple Music (AppleScript, no GUI needed), local files (afplay), QQ Music (search + preview).
- **Pixel UI** — Album art in half-block ANSI, GameBoy retro border, pseudo-spectrum equalizer.
- **DJ Buddy** — A headphones-wearing pixel character that reacts to your coding state. Tests failing? It panics with you.
- **Vibe engine** — CC hooks track what you're doing in real time and shift the mood. `git commit`? Victory pose. Tests explode? Panic mode.
- **Statusline** — One line: face + current track + progress bar.
- **Focus mode** — Built-in 25/5 Pomodoro timer shown in the statusline.

---

## Installation

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
```

Or manually:

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install.sh
```

The installer configures Claude Code to use the HTTP MCP endpoint at `http://127.0.0.1:8765/mcp`, saves that URL to `~/.coding-with-beat/mcp-url`, and on macOS starts a user LaunchAgent for the local MCP server. For debugging, you can run it by hand:

```bash
cwb server --host 127.0.0.1 --port 8765 --path /mcp
```

Open a new shell and a new Claude Code session. When `(•_•)` appears in the statusline, you're good.

---

## Usage

### Just talk to Claude

```
play some lofi
skip this track
what's playing
pause
```

### `/cwb` command

```
/cwb play "lofi beats"    # search and play
/cwb play lofi beats
/cwb search "lofi beats"  # search library + Apple Music, show numbered list
/cwb play 2               # play track #2 from last search / list results
/cwb list                 # list all library tracks
/cwb next
/cwb pause
/cwb np                   # now playing
/cwb like
/cwb volume 70
/cwb watch                # live player (q to quit)
/cwb karaoke              # full-screen karaoke (q to quit)
/cwb lyrics               # lyrics window
/cwb bar auto             # statusline: auto / show / hide
```

Natural-language commands work too: `skip this track`, `pause`, `what's playing`, and `like this` are all valid.

### `watch` / `karaoke` shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play / pause |
| `n` | Next |
| `p` | Previous |
| `l` | Like |
| `q` | Quit |

---

## Statusline

Once installed, a statusline appears at the bottom of Claude Code:

```
(•_•) ⚡  ▶ Midnight City — M83  ██████░░░░░░░░  [build]  ▃▆█▆▃  │ ♪ lyric preview
```

| Element | Example | Description |
|---------|---------|-------------|
| DJ face | `(•_•)` `(^_^)` `(T_T)` | Buddy's mood, shifts with coding events |
| Activity | `⚡` / `·` / _(none)_ | `⚡` = tool call in last 15 s; `·` = last 90 s |
| Play icon | `▶` / `▷` / `❚❚` | Blinks while playing; ❚❚ when paused |
| Track | `Midnight City — M83  ██████░░░░░░░░` | Title + artist + progress bar |
| Vibe | `[build]` `[focus]` etc. | Current coding vibe |
| Pomodoro | `🍅 work 24:15` | Only shown when focus mode is active |
| Beat wave | `▁▂▃▄▅` | Rises and falls each beat; dims when paused |
| Lyrics | `│ ♪ lyrics here` | Current LRC lyric |

<details>
<summary>Little easter egg: show it anywhere</summary>

`cwb statusline` is the same renderer Claude Code uses. It reads optional JSON from stdin, uses `columns` as a width hint, and prints one compact status bar line to stdout.

```bash
printf '{"columns":120}' | cwb statusline
```

That makes it easy to plug into other status bars. For example, tmux can show CWB on the right side of its status bar:

#### tmux status-right

```tmux
set -g status-right-length 180
set -g status-interval 1
set -g status-right '#(printf "{\"columns\":170}" | cwb statusline | perl -pe "s/\e\[[0-9;]*m//g")'
```

`cwb statusline` currently emits ANSI-coloured terminal text. The `perl` bit strips ANSI escape codes because tmux status formats use their own styling syntax. Increase or decrease `columns` and `status-right-length` to control how much room lyrics get.

#### Neovim statusline

Neovim can also show CWB in its statusline. Keep the shell call asynchronous so editing never waits on music state:

```lua
local cwb = { text = "", running = false }

local function strip_ansi(text)
  return text:gsub("\27%[[0-9;]*m", "")
end

local function refresh()
  if cwb.running or vim.fn.executable("cwb") == 0 then
    return
  end
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

</details>

---

## SSH Remote Claude Code

If Claude Code runs on a server while Apple Music runs on your local Mac, run the streamable HTTP MCP server on the Mac and reach it from the server through SSH reverse port forwarding:

```bash
# Local Mac: install and start the HTTP MCP LaunchAgent
./install.sh

# Local Mac: expose it to the server's 127.0.0.1:8765
ssh -N -R 127.0.0.1:8765:127.0.0.1:8765 user@server

# Server: install hooks/statusline and point them at the forwarded endpoint
./install.sh --mcp-url http://127.0.0.1:8765/mcp
```

The remote Claude Code session, `/cwb`, statusline, hooks, and `cwb` CLI all use the same HTTP MCP URL. As long as the SSH tunnel is up, commands like `cwb play`, `cwb np`, `cwb next`, `cwb player`, and `cwb karaoke` control the Mac-side music client.

---

## CLI

```
cwb play [query]        # search and play, or resume
cwb play <n>            # play track #n from last search or list results
cwb search <query>      # search library + Apple Music catalog (numbered list)
cwb list [n]            # list all library tracks (default 100)
cwb pause               # pause
cwb next                # next track
cwb prev                # previous track
cwb np                  # now playing
cwb like                # like current track
cwb volume <0-100>      # set volume
cwb seek <t>            # seek: seconds (90) or mm:ss (1:30)
cwb mode <mode>         # shuffle | sequential | repeat | repeat_one
cwb player              # full pixel player
cwb watch               # live TUI (q to quit)
cwb karaoke             # full-screen karaoke (q to quit)
cwb lyrics              # lyrics window
cwb history [n]         # last n played tracks
cwb bar <show|hide|auto> # statusline visibility
cwb statusline          # render one compact statusline frame
cwb status              # current state
cwb server              # MCP streamable HTTP server
```

---

## Music sources

| Feature | Apple Music | Local files | QQ Music |
|---------|-------------|-------------|----------|
| Now playing info | ✓ | ✓ | ⚠ preview only |
| Play / pause | ✓ | ✓ | ✓ |
| Next / prev | ✓ | ✓ | ✓ |
| Seek | ✓ | ⚠ restart-based | ⚠ preview only |
| Volume | ✓ | ✓ | ⚠ coarse steps |
| Like / favorite | ✓ | ✗ | ✓ |
| Cover art | ✓ | ✓ | ✓ |
| Full playback | ✓ subscription req. | ✓ | ✗ 30 s preview |
| Play modes | ✓ | ✗ | ✓ |

> QQ Music has no official API. Search metadata comes from public endpoints; audio is played as 30-second preview clips via afplay. Full tracks require the QQ Music desktop app.

---

## Uninstall

```bash
./uninstall.sh           # remove config, commands, PATH
./uninstall.sh --purge   # same + delete ~/.coding-with-beat/
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
