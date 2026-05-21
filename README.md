# CC-Jukebox

A pixel-art music companion for Claude Code. Listen to music without leaving
the terminal, get a reactive retro UI, and let a tiny DJ Buddy change the
vibe as you code.

```
 ██████╗ ██████╗     ██╗██╗   ██╗██╗  ██╗███████╗██████╗  ██████╗ ██╗  ██╗
██╔════╝██╔════╝     ██║██║   ██║██║ ██╔╝██╔════╝██╔══██╗██╔═══██╗╚██╗██╔╝
██║     ██║          ██║██║   ██║█████╔╝ █████╗  ██████╔╝██║   ██║ ╚███╔╝
██║     ██║     ██   ██║██║   ██║██╔═██╗ ██╔══╝  ██╔══██╗██║   ██║ ██╔██╗
╚██████╗╚██████╗╚█████╔╝╚██████╔╝██║  ██╗███████╗██████╔╝╚██████╔╝██╔╝ ██╗
 ╚═════╝ ╚═════╝ ╚════╝  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═════╝  ╚═════╝ ╚═╝  ╚═╝
                   a pixel companion for vibecoding
```

## What it does

- **MCP server** — exposes 21 tools to Claude Code so you can say "play some
  lofi", "skip this", "show the player", "what's playing?" and have it work.
- **Music sources** — Apple Music (AppleScript, no GUI needed), local files
  (afplay), QQ Music (search + preview via public API).
- **Pixel UI** — album covers rendered as half-block ANSI, GameBoy 4-color
  palette mode, retro frame, reactive (deterministic-from-position) spectrum.
- **DJ Buddy** — a 5-line pixel character that changes mood with your work.
- **Vibe Engine** — CC hooks (PreToolUse/PostToolUse/SessionStart/Stop)
  watch your activity and update the mood/vibe in real time. Test fails →
  Buddy panics. Commit lands → victory chip.
- **Statusline** — compact one-liner with face + current track + progress.
- **Focus Loop** — 25/5 pomodoro that shows in the statusline.
- **One-click install** — `bootstrap.sh` / `install.sh` set up everything
  globally (venv, PATH, slash command, MCP server, hooks). No system Python
  required — falls back to [uv](https://docs.astral.sh/uv/) to fetch one if
  your machine doesn't have Python ≥3.10.

## Install

### One-liner (recommended)

```bash
curl -LsSf https://raw.githubusercontent.com/jaychempan/cc-jukebox/main/bootstrap.sh | sh
```

That clones cc-jukebox into `~/.cc-jukebox/src`, then runs `install.sh`.
Re-run anytime to update.

### Manual

```bash
git clone https://github.com/jaychempan/cc-jukebox.git
cd cc-jukebox
./install.sh
```

### What install.sh does

1. **Python** — finds a Python ≥3.10 on PATH, in `/opt/homebrew/bin`,
   `/usr/local/bin`, or any conda env under `~/miniconda3/envs` etc.
   If none of those exist, **automatically installs uv and uses it to
   download Python 3.12** (no system pollution; lives under `~/.local/`).
   Override with `CC_JUKEBOX_PYTHON=/path/to/python ./install.sh`.
2. **venv** at `~/.cc-jukebox/venv` (not in the repo dir, so the install
   survives moving / deleting the source).
3. **`cc-jukebox` CLI** symlinked into `~/.local/bin/` and (idempotently)
   appends a marked `export PATH=…` block to `~/.zshrc` (and `~/.bashrc`)
   so the command is reachable from any new shell.
4. **`/juke` slash command** symlinked from `commands/juke.md` into
   `~/.claude/commands/` — the repo is the source of truth, so a
   `git pull` updates the command without re-running install.
5. **Claude Code settings** — merges entries into `~/.claude/settings.json`:
   - `mcpServers["cc-jukebox"]`
   - `statusLine` (only if you don't already have one)
   - hooks for `PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`
6. **State dir** `~/.cc-jukebox/` for runtime JSON.

Each entry is tagged with `_owner: "cc-jukebox"` so `./uninstall.sh` can
remove only what we added.

Start a new shell (so PATH picks up the new entry) and a new Claude Code
session. You should see a `(•_•)` face in the statusline. Try saying:

> show me the player

…and Claude will call `show_player`, painting the pixel frame inline. Or
type `/juke play 周杰伦` to drive it directly.

## Project-level config

In any project directory:

```bash
cc-jukebox init
```

…writes `.cc-jukebox.toml` so different projects can default to different
vibes / sources / starter queries.

## CLI

After `install.sh`, the `cc-jukebox` command is on your PATH.

```
cc-jukebox status              # current state
cc-jukebox np                  # one-line: title — artist
cc-jukebox play [query]        # resume, or search & play (see below)
cc-jukebox pause
cc-jukebox next
cc-jukebox prev
cc-jukebox player              # full pixel player frame
cc-jukebox watch               # ticking TUI (Ctrl-C to exit)
cc-jukebox cover [rgb|gameboy] # current cover only
cc-jukebox lyrics              # karaoke window
cc-jukebox demo                # visual smoke test
cc-jukebox banner              # the giant banner
cc-jukebox init                # write .cc-jukebox.toml
cc-jukebox server              # MCP server (CC starts this for you)
cc-jukebox statusline          # one statusline frame (CC calls this)
cc-jukebox hook                # CC hook receiver (stdin = JSON event)
```

### `cc-jukebox play` search behaviour

Apple Music search is three-tiered (cheapest first):

1. **Local-library substring** — `every track of library playlist 1 whose
   name contains "Q" or artist contains "Q"`. Fast, exact.
2. **Multi-token AND** — `"青花瓷 周杰伦"` → tracks where each token hits
   `name` or `artist`. Lets natural "song artist" queries work even when no
   single field contains the whole string.
3. **iTunes Search API** — if nothing local matches, hit Apple's public
   search endpoint and ask Music.app to open the top hit's catalog URL
   (`music://music.apple.com/song/<id>`). Requires an active Apple Music
   subscription to actually play; otherwise Music will just show the page.

### `/juke` slash command

Installed at `~/.claude/commands/juke.md` (symlinked to this repo). Inside
Claude Code:

```
/juke status
/juke play 稻香 周杰伦
/juke next
/juke pause
/juke np
```

Accepts free-form Chinese or English intents (`下一首`, `暂停`, `在放什么`).

## Source capability matrix

| Source       | now_playing | play/pause | skip | seek | search       | full playback | cover art |
|--------------|-------------|------------|------|------|--------------|---------------|-----------|
| apple_music  | ✓ (osascript) | ✓          | ✓    | ✓    | ✓ (library)  | ✓             | ✓         |
| local        | ✓ (PID + clock) | ✓ (kill/respawn) | ✓ (next file) | ⚠ best-effort | ✓ (filename) | ✓        | ✓ (id3)   |
| qq_music     | partial       | ✓ (preview only) | —    | —    | ✓ (HTTP API) | ⚠ 30s preview only | ✓ |

QQ Music has no AppleScript hook and no official public API. We use the
unofficial search endpoint for metadata and try to play 30-second previews.
Full paid-track playback requires the QQ Music desktop app and is not
something we can drive headlessly.

## Vibe rules (default)

| Event                                     | Mood       | Vibe     |
|-------------------------------------------|------------|----------|
| `SessionStart`                            | happy      | focus    |
| `Edit` / `Write` / `MultiEdit`            | focus      | from ext (py/ts → build, sql → focus, md → review) |
| `Read` / `Grep` / `Glob`                  | thinking   | review   |
| `Bash` containing `pytest`/`npm test`/etc | victory or sad | victory or fail |
| `Bash` containing `git commit`            | victory    | victory  |
| `Stop`                                    | sleep      | idle     |

Override at any time:

> set vibe to debug
> dj say something cheerful

(These trigger the `vibe_set` and `dj_say` MCP tools.)

## Files

```
cc_jukebox/
├── __main__.py            # CLI dispatcher
├── server.py              # MCP server (21 tools)
├── statusline.py          # one-frame statusline
├── vibe.py                # hook receiver + classifier
├── focus.py               # pomodoro loop
├── dj.py                  # DJ Buddy character (faces, sprites, quips)
├── state.py               # JSON-backed shared state
├── config.py              # paths + palettes + vibe maps
├── sources/
│   ├── apple_music.py     # AppleScript
│   ├── local.py           # afplay + mutagen tags
│   └── qq_music.py        # HTTP search + preview
└── ui/
    ├── pixel_cover.py     # image → half-block ANSI
    ├── progress.py        # progress bar + pseudo-spectrum
    ├── frame.py           # retro pixel border + banner
    └── lyrics.py          # karaoke-style window
```

## Caveats

- **macOS only.** Apple Music + afplay are macOS-specific. Linux/Windows
  would need replacement backends.
- **The "spectrum" is fake.** We can't capture system audio from terminal,
  so the bars animate deterministically from `position`. It looks alive
  without lying about being a real FFT.
- **DJ Buddy will not shut up if you let it.** It only speaks when CC calls
  `dj_say`. The hooks just update state.

## Uninstall

```bash
./uninstall.sh           # drops settings.json entries, the cc-jukebox bin
                         # symlink, the /juke command, and the PATH block
                         # in ~/.zshrc / ~/.bashrc.
./uninstall.sh --purge   # also deletes ~/.cc-jukebox/ (venv + state).
```
