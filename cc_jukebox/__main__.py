"""cc-jukebox CLI.

Usage:
    python -m cc_jukebox <command>

Commands:
    server       — start the MCP server over streamable HTTP
    statusline   — emit one statusline frame (used by CC)
    hook         — receive a CC hook event JSON on stdin and update vibe
    init         — scaffold .cc-jukebox.toml in the current directory
    status       — print human-readable current state
    welcome      — show the install welcome logo
    demo         — render a demo player frame (great for visual testing)
    banner       — print the retro banner
    cover        — render the current track's cover as pixel art
    lyrics       — render a karaoke window for the current track
    player       — render the full live player (cover + progress + lyrics + buddy)
    watch        — real-time ticking player in an alt-screen TUI (Ctrl-C to exit)
    source [name] — print or set source (apple_music | local | qq_music)
    karaoke      — full-screen centred lyrics from the MCP server (Ctrl-C to exit)
    play [query] — resume current track, or search & play if a query is given
    pause        — pause playback
    next         — skip to next track
    prev         — go to previous track
    np           — print current track (title — artist)
    like         — like/favorite the current track on the active source
    mode <mode>  — set play mode: shuffle | sequential | repeat | repeat_one
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _mcp_print(tool: str, kwargs: dict | None = None) -> int:
    from .mcp_client import MCPClientError, call_tool
    try:
        output = call_tool(tool, kwargs or {})
    except MCPClientError as e:
        print(str(e), file=sys.stderr)
        return 1
    if output:
        print(output)
    return 0


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
    return _mcp_print("status")


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
    return _mcp_print("banner")


def cmd_welcome() -> int:
    from .ui.frame import welcome_screen
    print(welcome_screen())
    return 0


def cmd_cover() -> int:
    style = sys.argv[2] if len(sys.argv) > 2 else "rgb"
    return _mcp_print("show_cover", {"style": style, "width": 40, "height": 20})


def cmd_lyrics() -> int:
    window = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    return _mcp_print("show_lyrics", {"window": window})


def cmd_player() -> int:
    return _mcp_print("show_player", {"width": 40, "with_lyrics": True})


def cmd_watch() -> int:
    from .watch import run
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 44
    return run(width=width)


def cmd_source() -> int:
    if len(sys.argv) < 3:
        return _mcp_print("current_source")
    name = sys.argv[2]
    return _mcp_print("set_source", {"name": name})


def cmd_karaoke() -> int:
    from .karaoke import run
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    return run(width=width)


def cmd_play() -> int:
    """play [query] — resume if no query, otherwise search and play."""
    query = " ".join(sys.argv[2:]).strip()
    if query:
        return _mcp_print("play_song", {"query": query})
    return _mcp_print("play")


def cmd_pause() -> int:
    return _mcp_print("pause")


def cmd_next() -> int:
    return _mcp_print("next_track")


def cmd_prev() -> int:
    return _mcp_print("prev_track")


def cmd_np() -> int:
    return _mcp_print("now_playing")


def cmd_like() -> int:
    return _mcp_print("like_current")


def cmd_mode() -> int:
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    if not mode:
        print("error: mode is required")
        return 2
    return _mcp_print("set_play_mode", {"mode": mode})


def cmd_prefetch() -> int:
    """Internal: silently fetch and cache lyrics for the current track."""
    from . import state
    from .sources import get_source
    from .config import DATA_DIR
    import re
    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "lyrics", None)
    if callable(fn):
        try:
            fn()
        except Exception:
            pass
    # Remove the lock file so statusline can trigger again on track change
    t = st.track
    if t.title:
        key = re.sub(r"[^a-zA-Z0-9一-鿿]+", "_",
                     f"{t.artist}_{t.album}_{t.title}").strip("_")[:160]
        prefix = {"apple_music": "am", "local": "local", "qq_music": "qq"}.get(st.source, "am")
        lock = DATA_DIR / f".lyfetch_{prefix}_{key}"
        lock.unlink(missing_ok=True)
    return 0


def cmd_server() -> int:
    import argparse
    from .server import main

    ap = argparse.ArgumentParser(prog="cc-jukebox server")
    ap.add_argument("--host", default=os.environ.get("CC_JUKEBOX_MCP_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=_env_int("CC_JUKEBOX_MCP_PORT", 8765))
    ap.add_argument("--path", default=os.environ.get("CC_JUKEBOX_MCP_PATH", "/mcp"))
    ap.add_argument("--stateless", action="store_true")
    ap.add_argument("--log-level", default=os.environ.get("CC_JUKEBOX_MCP_LOG_LEVEL", "info"))
    args = ap.parse_args(sys.argv[2:])

    main(
        host=args.host,
        port=args.port,
        path=args.path,
        stateless_http=args.stateless,
        log_level=args.log_level,
    )
    return 0


def cmd_statusline() -> int:
    from .statusline import main
    return main()


def cmd_hook() -> int:
    from .vibe import main
    return main()


COMMANDS = {
    "_prefetch": cmd_prefetch,
    "server": cmd_server,
    "statusline": cmd_statusline,
    "hook": cmd_hook,
    "init": cmd_init,
    "status": cmd_status,
    "welcome": cmd_welcome,
    "demo": cmd_demo,
    "banner": cmd_banner,
    "cover": cmd_cover,
    "lyrics": cmd_lyrics,
    "player": cmd_player,
    "watch": cmd_watch,
    "source": cmd_source,
    "karaoke": cmd_karaoke,
    "play": cmd_play,
    "pause": cmd_pause,
    "next": cmd_next,
    "prev": cmd_prev,
    "np": cmd_np,
    "like": cmd_like,
    "favorite": cmd_like,
    "mode": cmd_mode,
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
