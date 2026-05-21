# Coding With Beat

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-macOS-000000?style=flat-square&logo=apple&logoColor=white)
![Claude Code](https://img.shields.io/badge/Claude_Code-compatible-c85f41?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-21_tools-7c5cbf?style=flat-square)
![Apple Music](https://img.shields.io/badge/Apple_Music-supported-FC3C44?style=flat-square)
![Version](https://img.shields.io/badge/version-0.1.0-9bbc0f?style=flat-square)

> **When was the last time you sang and danced while vibecoding?**
>
> Right. You can't remember.

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

You're just typing code. Claude watches quietly beside you. The cursor blinks in silence.
This tool exists to end that tragedy.

**Coding With Beat** is a pixel-art DJ companion that lives inside Claude Code.
It plays music, shows lyrics, celebrates when you commit, and panics with you when tests fail.

[中文文档](README.md)

---

## What it does

- **MCP server** — 21 tools so you can tell Claude "play some lofi", "skip this track", "what's playing" — it just works.
- **Music sources** — Apple Music (AppleScript, no GUI needed), local files (afplay), QQ Music (search + preview).
- **Pixel UI** — Album art rendered in half-block ANSI characters, GameBoy 4-color mode, retro borders, and a "looks-almost-real" spectrum equalizer.
- **DJ Buddy** — A pixel-art character with headphones that reacts to your coding state. Tests failing? It panics with you.
- **Vibe engine** — CC hooks (PreToolUse / PostToolUse / SessionStart / Stop) track what you're doing in real time and shift the mood. `git commit`? Victory fanfare. Tests explode? Buddy enters panic mode.
- **Statusline** — One line: tiny face + current track + progress bar. Always know where you are.
- **Focus mode** — Built-in 25/5 Pomodoro timer shown in the statusline, so you can pretend to be disciplined.
- **One-shot install** — `bootstrap.sh` / `install.sh` sets everything up globally. No Python? It uses [uv](https://docs.astral.sh/uv/) to grab one automatically.

---

## Installation

### One liner (recommended)

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh
```

Clones to `~/.coding-with-beat/src` and runs `install.sh`. To update, just run it again.

### Manual

```bash
git clone https://github.com/jaychempan/coding-with-beat.git
cd coding-with-beat
./install.sh
```

### What `install.sh` does

1. **Finds Python** — looks for Python ≥3.10 on PATH, Homebrew, or conda. Nothing found? Installs uv and downloads Python 3.12. Your system stays clean. Override with `CWB_PYTHON=/path/to/python ./install.sh`.
2. **Creates a venv** — at `~/.coding-with-beat/venv`, outside the project directory. Delete the source, the venv lives on.
3. **`cwb` command** — symlinked into `~/.local/bin/` with a PATH export added to `~/.zshrc` / `~/.bashrc`.
4. **`/cwb` slash command** — symlinked into `~/.claude/commands/`, pointing at the repo file so `git pull` auto-updates it.
5. **Claude Code config** — merges into `~/.claude/settings.json`: MCP server, statusline, vibe hooks, and the UserPromptExpansion hook for `/cwb`.
6. **State directory** — `~/.coding-with-beat/` for runtime JSON.

Every config entry is tagged `_owner: "coding-with-beat"` so uninstall removes exactly what it added — nothing else.

After install, open a new shell and a new Claude Code session. When `(•_•)` appears in the statusline, you're good. Try:

> Help me open the player

Claude calls `show_player` and draws the pixel player in the terminal. Or go direct: `/cwb play lofi`.

---

## Statusline

Once installed, a statusline appears at the bottom of Claude Code:

```
(•_•) ⚡  ▶ 雨爱 — 杨丞琳  ██████░░░░░░░░  [build]  ▃▆█▆▃  │ ♪ 不忍揭曉的劇情
```

Left to right:

| Element | Example | Description |
|---------|---------|-------------|
| DJ face | `(•_•)` `(^_^)` `(T_T)` | Buddy's current mood, changes with coding events |
| Activity | `⚡` / `·` / _(none)_ | `⚡` = tool call in last 15 s; `·` = last 90 s; blank = cooled down |
| Play icon | `▶` / `▷` (blinks) / `❚❚` | Alternates ▶ ▷ while playing; ❚❚ when paused |
| Track | `雨爱 — 杨丞琳  ██████░░░░░░░░` | Title + artist + 14-cell progress bar |
| Vibe | `[build]` `[focus]` etc. | Current coding vibe, color shifts with mood |
| Pomodoro | `🍅 work 24:15` `☕ break 04:30` | Only shown when focus mode is active |
| Beat wave | `▁▂▃▄▅` | BPM derived from track hash, rises and falls each beat; dim flat line when paused |
| Lyrics | `│ ♪ lyrics here` / `│ ✦ quip` | Current LRC lyric; briefly replaced by ✦ quip when DJ says something |

On narrow terminals, lyrics truncate first; narrower still and the wave + lyrics hide, but track info always stays visible.

---

## Per-project config

In any project directory:

```bash
cwb init
```

Generates `.coding-with-beat.toml` so different projects get different default vibes, sources, and playlists. lo-fi while writing Python, city pop while writing Makefiles — makes sense.

---

## CLI reference

```
cwb status              # Current state
cwb np                  # One line: title — artist
cwb play [query]        # Resume, or search and play
cwb pause               # Pause
cwb next                # Next track
cwb prev                # Previous track
cwb like                # Like / favorite current track
cwb mode <mode>         # Playback mode: shuffle | sequential | repeat | repeat_one
cwb volume <0-100>      # Set volume
cwb seek <t>            # Seek: seconds (90) or mm:ss (1:30)
cwb player              # Full pixel player
cwb watch               # TUI live mode (keyboard controls, q to quit)
cwb karaoke             # Full-screen karaoke mode (keyboard controls, q to quit)
cwb cover [rgb|gameboy] # Album art only
cwb lyrics              # Lyrics window
cwb history [n]         # Last n played tracks (default 10)
cwb bar <show|hide|auto> # Statusline: show = always, hide = never, auto = only while playing
cwb demo                # Visual test
cwb banner              # Big wordmark banner
cwb init                # Generate .coding-with-beat.toml
cwb server              # MCP server (CC starts this automatically)
cwb statusline          # Render one statusline frame (used by CC)
cwb hook                # CC hook receiver (stdin = JSON event)
```

### `watch` / `karaoke` keyboard shortcuts

Once in a live TUI mode, control playback without exiting:

| Key | Action |
|-----|--------|
| `Space` | Play / pause |
| `n` | Next track |
| `p` | Previous track |
| `l` | Like current track |
| `q` | Quit |

### `play` search logic

Apple Music search runs three stages, fastest first:

1. **Local library substring match** — `name` or `artist` contains the keyword. Instant.
2. **Multi-word AND match** — `"青花瓷 周杰伦"` → each word must hit `name` or `artist`. Works with natural language queries too.
3. **iTunes Search API** — not in local library? Hits Apple's public search API, gets a catalog URL, and opens it in Music.app. Requires an active Apple Music subscription to actually play.

### `/cwb` slash command

After install, use it directly in Claude Code:

```
/cwb status
/cwb play lofi beats
/cwb next
/cwb pause
/cwb np
/cwb volume 70
/cwb seek 1:30
/cwb like
/cwb bar show           # always show statusline
/cwb bar hide           # hide statusline
/cwb bar auto           # show only while playing
```

Chinese and English both work — `下一首`, `暂停`, `在放什么`, `收藏` are all valid.

**Fast path**: Common commands (pause, next, prev, np, like, volume, seek, etc.) match locally without spawning a Claude subprocess — response drops from ~5 s to <0.1 s. Only ambiguous natural-language requests ("play something chill") go through a headless Claude session. The main conversation never sees the music-control detail.

---

## Source capability matrix

| Source | Now playing | Play/pause | Skip | Position | Search | Full playback | Art |
|--------|-------------|------------|------|----------|--------|---------------|-----|
| apple_music | ✓ | ✓ | ✓ | ✓ | ✓ (local library) | ✓ | ✓ |
| local | ✓ | ✓ | ✓ | ⚠ | ✓ (filename) | ✓ | ✓ |
| qq_music | partial | ✓ (preview) | — | — | ✓ (HTTP) | ⚠ 30 s preview only | ✓ |

QQ Music has no AppleScript interface or public API. It uses an unofficial search endpoint with 30-second previews. Full playback requires the QQ Music app open — that's outside what we can drive.

---

## Vibe rules (defaults)

| Event | Mood | Vibe |
|-------|------|------|
| `SessionStart` | happy | focus |
| `Edit` / `Write` on test files (`test_*.py`, `*.spec.ts`, etc.) | focus | debug |
| `Edit` / `Write` / `MultiEdit` | focus | by extension (py/ts → build, sql → focus, md → review) |
| `Read` / `Grep` / `Glob` | thinking | review |
| `Bash` with `pytest` / `npm test` / etc. | victory or sad | victory or fail |
| `Bash` with `git commit` | victory | victory |
| `Stop` | sleep | idle |

Override anytime:

> switch to debug mode
> DJ, say something encouraging

This triggers `vibe_set` and `dj_say` tools.

---

## File layout

```
coding_with_beat/
├── __main__.py            # CLI entry point
├── server.py              # MCP server (21 tools)
├── statusline.py          # Single-frame statusline renderer
├── vibe.py                # Hook receiver + classifier
├── focus.py               # Pomodoro timer
├── dj.py                  # DJ Buddy (faces, sprites, quips)
├── state.py               # JSON state read/write
├── config.py              # Paths, palettes, vibe mappings
├── sources/
│   ├── apple_music.py     # AppleScript bridge
│   ├── local.py           # afplay + mutagen tags
│   └── qq_music.py        # HTTP search + preview
└── ui/
    ├── pixel_cover.py     # Image → half-block ANSI
    ├── progress.py        # Progress bar + pseudo-spectrum
    ├── frame.py           # Retro pixel border + banner
    └── lyrics.py          # Karaoke lyrics window
```

---

## Known limitations

- **macOS only.** Apple Music and afplay are macOS-specific. Linux / Windows would need a different backend — no plans for that currently.
- **The spectrum is fake.** There's no way to capture system audio in a terminal, so the equalizer bars are generated by a deterministic animation driven by playback position. It looks good, but it's not a real FFT.
- **DJ Buddy won't interrupt you.** It only speaks when Claude calls `dj_say`. Hooks update state silently and never pop anything up.

---

## Uninstall

```bash
./uninstall.sh           # Remove settings.json entries, cwb command, /cwb command, PATH block
./uninstall.sh --purge   # Same, plus deletes ~/.coding-with-beat/ (venv + state files)
```
