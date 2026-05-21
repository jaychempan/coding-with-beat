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
- **One-click install** — `install.sh` patches `~/.claude/settings.json` for
  you (idempotent; safe to re-run).

## Install

```bash
cd cc-jukebox
./install.sh
```

This will:
1. Create `.venv/` using the best Python ≥3.10 it can find.
2. Install `mcp`, `Pillow`, `rich`, `mutagen`, `httpx`.
3. Merge entries into `~/.claude/settings.json`:
   - `mcpServers["cc-jukebox"]`
   - `statusLine` (only if you don't already have one)
   - hooks for `PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`
4. Create `~/.cc-jukebox/` for state.

Each entry is tagged with `_owner: "cc-jukebox"` so `./uninstall.sh` can
remove only what we added.

Start a new Claude Code session after installing and you should see a `(•_•)`
face in the statusline. Try saying:

> show me the player

…and Claude will call `show_player`, painting the pixel frame inline.

## Project-level config

In any project directory:

```bash
python -m cc_jukebox init
```

…writes `.cc-jukebox.toml` so different projects can default to different
vibes / sources / starter queries.

## CLI

```
python -m cc_jukebox server       # the MCP server (CC starts this for you)
python -m cc_jukebox statusline   # one statusline frame (CC calls this)
python -m cc_jukebox hook         # CC hook receiver (stdin = JSON event)
python -m cc_jukebox init         # write project config
python -m cc_jukebox status       # print current state
python -m cc_jukebox demo         # render a demo player (visual smoke test)
python -m cc_jukebox banner       # print the giant banner
python -m cc_jukebox cover [style]  # render current cover (rgb|gameboy)
```

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
./uninstall.sh           # remove from ~/.claude/settings.json
./uninstall.sh --purge   # also delete ~/.cc-jukebox/
```
