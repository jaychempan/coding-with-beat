# Coding With Beat

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-c85f41?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-21_tools-7c5cbf?style=flat-square)
![Apple Music](https://img.shields.io/badge/Apple_Music-supported-FC3C44?style=flat-square)
![Version](https://img.shields.io/badge/version-0.1.0-9bbc0f?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

> **When was the last time you sang and danced while vibecoding?**（上次 vibecoding 时又唱又跳是什么时候？）
>
> Right. You can't remember.（对，你已经不记得了。）

```
                            ╭─────────────────╮
                            │ ╭─────────────╮ │
                            │ │  ╭───────╮  │ │
                            │ │  │   ◉   │  │ │
                            │ │  ╰───────╯  │ │
                            │ ╰─────────────╯ │
                            ╰─────────────────╯

               (♪‿♪)   a pixel companion for vibecoding   (♪‿♪)

                               C  O  D  I  N  G
 ██╗    ██╗██╗████████╗██╗  ██╗    ██████╗ ███████╗ █████╗ ████████╗
 ██║    ██║██║╚══██╔══╝██║  ██║    ██╔══██╗██╔════╝██╔══██╗╚══██╔══╝
 ██║ █╗ ██║██║   ██║   ███████║    ██████╔╝█████╗  ███████║   ██║
 ██║███╗██║██║   ██║   ██╔══██║    ██╔══██╗██╔══╝  ██╔══██║   ██║
 ╚███╔███╔╝██║   ██║   ██║  ██║    ██████╔╝███████╗██║  ██║   ██║
  ╚══╝╚══╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝    ╚═════╝ ╚══════╝╚═╝  ╚═╝   ╚═╝

 ────────────────────────────────────────────────────────────────────────────
    ✓  MCP server registered                ✓  /cwb command installed
    ✓  CC hooks active                      ✓  statusline ready
 ────────────────────────────────────────────────────────────────────────────

    open Claude Code and say: "play some lofi"  ·  or /cwb play 周杰伦
```

A pixel-art DJ companion that lives inside Claude Code. It plays music, shows lyrics, celebrates when you commit, and panics with you when tests fail.

[中文文档](README_CN.md) ／ [日本語](README_JP.md)

---

## Features

- **MCP server** — 21 tools so you can tell Claude "play some lofi", "skip this", "what's playing" and it just works.
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
/cwb play 周杰伦          # search and play
/cwb play lofi beats
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

Chinese works too — `下一首`, `暂停`, `在放什么`, `收藏` are all valid.

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
(•_•) ⚡  ▶ 雨爱 — 杨丞琳  ██████░░░░░░░░  [build]  ▃▆█▆▃  │ ♪ 不忍揭曉的劇情
```

| Element | Example | Description |
|---------|---------|-------------|
| DJ face | `(•_•)` `(^_^)` `(T_T)` | Buddy's mood, shifts with coding events |
| Activity | `⚡` / `·` / _(none)_ | `⚡` = tool call in last 15 s; `·` = last 90 s |
| Play icon | `▶` / `▷` / `❚❚` | Blinks while playing; ❚❚ when paused |
| Track | `雨爱 — 杨丞琳  ██████░░░░░░░░` | Title + artist + progress bar |
| Vibe | `[build]` `[focus]` etc. | Current coding vibe |
| Pomodoro | `🍅 work 24:15` | Only shown when focus mode is active |
| Beat wave | `▁▂▃▄▅` | Rises and falls each beat; dims when paused |
| Lyrics | `│ ♪ lyrics here` | Current LRC lyric |

---

## CLI

```
cwb play [query]        # search and play, or resume
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
cwb status              # current state
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
