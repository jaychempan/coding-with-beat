"""cc-jukebox CLI.

Usage:
    python -m cc_jukebox <command>

Commands:
    server       — start the MCP server (used by CC)
    statusline   — emit one statusline frame (used by CC)
    hook         — receive a CC hook event JSON on stdin and update vibe
    init         — scaffold .cc-jukebox.toml in the current directory
    status       — print human-readable current state
    demo         — render a demo player frame (great for visual testing)
    banner       — print the retro banner
    cover        — render the current track's cover as pixel art
    lyrics       — render a karaoke window for the current track
    player       — render the full live player (cover + progress + lyrics + buddy)
    watch        — real-time ticking player in an alt-screen TUI (Ctrl-C to exit)
    play [query] — resume current track, or search & play if a query is given
    pause        — pause playback
    next         — skip to next track
    prev         — go to previous track
    np           — print current track (title — artist)
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def cmd_init() -> int:
    target = Path.cwd() / ".cc-jukebox.toml"
    if target.exists():
        print(f"already exists: {target}")
        return 0
    project_name = Path.cwd().name
    target.write_text(f'''# cc-jukebox project config — auto-loaded when CC runs in this directory.
project = "{project_name}"

# default vibe for this project. Options:
# focus | build | debug | victory | fail | idle | review
default_vibe = "build"

# preferred music source. apple_music | local | qq_music
source = "apple_music"

# starting playlist / query. When CC starts a session here, cc-jukebox will
# attempt to play this on session start (only if `auto_play_on_session = true`).
default_query = ""
auto_play_on_session = false

# per-file-extension overrides. extension → vibe
[file_vibes]
py = "build"
ts = "build"
sql = "focus"
md = "review"
''')
    print(f"created {target}")
    print("Edit it to set your default vibe and starter query.")
    return 0


def cmd_status() -> int:
    from . import state, focus
    st = state.load()
    f = focus.status()
    print(f"source : {st.source}")
    print(f"vibe   : {st.vibe}  (mood={st.dj_mood})")
    print(f"focus  : {f.phase if f.active else 'off'}"
          + (f" — {f.remaining}s left" if f.active else ""))
    if st.track.title:
        print(f"track  : {st.track.title} — {st.track.artist}")
        print(f"         {int(st.track.position)}s / {int(st.track.duration)}s "
              + ("▶" if st.playing else "❚❚"))
    else:
        print("track  : (none)")
    return 0


def cmd_demo() -> int:
    from . import state, dj
    from .ui import boxed, render_cover, render_progress, retro_banner
    from .ui.progress import render_spectrum_color

    st = state.load()
    print(retro_banner("DEMO MODE"))
    print()

    cover = render_cover(st.track.artwork_path or None, width=32, height=14)
    title = st.track.title or "Untitled Track"
    artist = st.track.artist or "Unknown Artist"
    pos = st.track.position or 73.0
    dur = st.track.duration or 217.0
    body = (
        f"{cover}\n"
        f"\x1b[1;38;2;255;230;100m♪ {title}\x1b[0m\n"
        f"\x1b[38;2;180;180;200m  {artist}\x1b[0m\n"
        f"{render_progress(pos, dur, width=32)}\n"
        f"{render_spectrum_color(pos, width=32)}\n"
        f"\x1b[38;2;155;188;15m{dj.sprite(st.dj_mood or 'groove')}\x1b[0m\n"
        f"\x1b[3;38;2;200;200;230m  “{dj.quip(st.dj_mood or 'groove')}”\x1b[0m"
    )
    print(boxed(f"CC-JUKEBOX · {st.source}", body, width=40))
    return 0


def cmd_banner() -> int:
    from .ui import retro_banner
    print(retro_banner("a pixel companion for vibecoding"))
    return 0


def cmd_cover() -> int:
    from . import state
    from .ui import render_cover, render_cover_gameboy
    st = state.load()
    style = sys.argv[2] if len(sys.argv) > 2 else "rgb"
    if style == "gameboy":
        print(render_cover_gameboy(st.track.artwork_path or None, width=40, height=20))
    else:
        print(render_cover(st.track.artwork_path or None, width=40, height=20))
    return 0


def cmd_lyrics() -> int:
    from . import state
    from .sources import get_source
    from .ui.lyrics import render_lyrics_window
    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "lyrics", None)
    if not callable(fn):
        print(f"(source {st.source!r} does not support lyrics)")
        return 1
    np = src.now_playing()
    text = fn()
    if not text:
        print(f"(no lyrics for: {np.title or '(unknown)'} — {np.artist or '?'})")
        return 1
    window = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    print(f"\x1b[1;38;2;255;230;100m♪ {np.title}\x1b[0m  \x1b[38;2;120;130;130m— {np.artist}\x1b[0m")
    print(f"\x1b[38;2;120;130;130m  {int(np.position):>3}s / {int(np.duration):>3}s\x1b[0m")
    print()
    print(render_lyrics_window(text, position=np.position, duration=np.duration, window=window))
    return 0


def cmd_player() -> int:
    from . import state, dj
    from .sources import get_source
    from .ui import boxed, render_cover, render_progress
    from .ui.progress import render_spectrum_color
    from .ui.lyrics import render_lyrics_window

    st = state.load()
    src = get_source(st.source)
    np = src.now_playing()

    width = 40
    cover = render_cover(np.artwork_path, width=width, height=int(width * 0.45))
    title = np.title or "(no track)"
    artist = np.artist or "—"

    blocks = [
        cover,
        f"\x1b[1;38;2;255;230;100m♪ {title}\x1b[0m",
        f"\x1b[38;2;180;180;200m  {artist}\x1b[0m",
        render_progress(np.position, np.duration, width=width - 2),
        render_spectrum_color(np.position, width=width - 2),
    ]

    fn = getattr(src, "lyrics", None)
    if callable(fn):
        text = fn()
        if text:
            blocks.append("\x1b[38;2;90;90;105m─── lyrics ───\x1b[0m")
            blocks.append(render_lyrics_window(
                text, position=np.position, duration=np.duration, window=5
            ))

    blocks.append(f"\x1b[38;2;155;188;15m{dj.sprite(st.dj_mood or 'neutral')}\x1b[0m")
    blocks.append(f"\x1b[3;38;2;200;200;230m  “{dj.quip(st.dj_mood or 'neutral')}”\x1b[0m")
    print(boxed(f"CC-JUKEBOX · {st.source}", "\n".join(blocks), width=max(width + 4, 44)))
    return 0


def cmd_watch() -> int:
    from .watch import run
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 44
    return run(width=width)


def _print_np(np) -> int:
    if np and getattr(np, "title", None):
        print(f"{np.title} — {np.artist or '?'}")
        return 0
    print("(no track)")
    return 1


def cmd_play() -> int:
    """play [query] — resume if no query, otherwise search and play."""
    from . import state
    from .sources import get_source
    import time
    src = get_source(state.load().source)
    query = " ".join(sys.argv[2:]).strip()
    if query:
        np = src.play_query(query)
    else:
        src.play()
        time.sleep(0.4)
        np = src.now_playing()
    return _print_np(np)


def cmd_pause() -> int:
    from . import state
    from .sources import get_source
    src = get_source(state.load().source)
    src.pause()
    np = src.now_playing()
    return _print_np(np)


def cmd_next() -> int:
    from . import state
    from .sources import get_source
    import time
    src = get_source(state.load().source)
    src.next()
    time.sleep(0.4)  # Apple Music needs a tick before now_playing reflects the new track
    return _print_np(src.now_playing())


def cmd_prev() -> int:
    from . import state
    from .sources import get_source
    import time
    src = get_source(state.load().source)
    src.prev()
    time.sleep(0.4)
    return _print_np(src.now_playing())


def cmd_np() -> int:
    from . import state
    from .sources import get_source
    src = get_source(state.load().source)
    return _print_np(src.now_playing())


def cmd_server() -> int:
    from .server import main
    main()
    return 0


def cmd_statusline() -> int:
    from .statusline import main
    return main()


def cmd_hook() -> int:
    from .vibe import main
    return main()


COMMANDS = {
    "server": cmd_server,
    "statusline": cmd_statusline,
    "hook": cmd_hook,
    "init": cmd_init,
    "status": cmd_status,
    "demo": cmd_demo,
    "banner": cmd_banner,
    "cover": cmd_cover,
    "lyrics": cmd_lyrics,
    "player": cmd_player,
    "watch": cmd_watch,
    "play": cmd_play,
    "pause": cmd_pause,
    "next": cmd_next,
    "prev": cmd_prev,
    "np": cmd_np,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"unknown command: {cmd}\n")
        print(__doc__)
        return 2
    return COMMANDS[cmd]() or 0


if __name__ == "__main__":
    sys.exit(main())
