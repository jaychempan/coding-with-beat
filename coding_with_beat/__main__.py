"""coding-with-beat CLI.

Usage:
    python -m coding_with_beat <command>

Commands:
    server       — start the MCP server over streamable HTTP
    statusline   — emit one statusline frame (used by CC)
    hook         — receive a CC hook event JSON on stdin and update vibe
    init         — scaffold .coding-with-beat.toml in the current directory
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
    volume <n>   — set playback volume 0-100
    seek <t>     — seek to position: seconds (90) or mm:ss (1:30)
    history [n]  — show last n tracks played (default 10)
    bar [mode]   — statusline visibility: show | hide | auto (print current if no arg)
    help         — show command reference (also: /cwb help, /cwb 帮助)
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
    target = Path.cwd() / ".coding-with-beat.toml"
    if target.exists():
        print(f"already exists: {target}")
        return 0
    project_name = Path.cwd().name
    target.write_text(f'''# coding-with-beat project config — auto-loaded when CC runs in this directory.
project = "{project_name}"

# default vibe for this project. Options:
# focus | build | debug | victory | fail | idle | review
default_vibe = "build"

# preferred music source. apple_music | local | qq_music
source = "apple_music"

# starting playlist / query. When CC starts a session here, coding-with-beat will
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
    print(boxed(f"CWB · {st.source}", body, width=40))
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


def cmd_volume() -> int:
    if len(sys.argv) < 3:
        print("error: usage: volume <0-100>")
        return 2
    try:
        vol = int(sys.argv[2])
    except ValueError:
        print("error: volume must be an integer 0-100")
        return 2
    vol = max(0, min(100, vol))
    return _mcp_print("set_volume", {"percent": vol})


def cmd_seek() -> int:
    if len(sys.argv) < 3:
        print("error: usage: seek <seconds> or seek <mm:ss>")
        return 2
    arg = sys.argv[2]
    try:
        if ":" in arg:
            mm, ss = arg.split(":", 1)
            seconds = int(mm) * 60 + float(ss)
        else:
            seconds = float(arg)
    except (ValueError, IndexError):
        print("error: invalid time — use seconds (e.g. 90) or mm:ss (e.g. 1:30)")
        return 2
    return _mcp_print("seek", {"seconds": seconds})


def cmd_bar() -> int:
    from . import state
    st = state.load()
    if len(sys.argv) < 3:
        print(f"statusline mode: {st.statusline_mode or 'show'}")
        return 0
    mode = sys.argv[2].lower()
    if mode not in ("show", "hide", "auto"):
        print("error: mode must be show | hide | auto")
        return 2
    st.statusline_mode = mode
    state.save(st)
    labels = {
        "show": "statusline on",
        "hide": "statusline hidden",
        "auto": "statusline auto (shows when playing)",
    }
    print(labels[mode])
    return 0


def cmd_history() -> int:
    from .config import DATA_DIR
    hist_file = DATA_DIR / "history.log"
    if not hist_file.exists():
        print("(no history yet — run 'watch' or 'karaoke' to start recording)")
        return 0
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    lines = hist_file.read_text(encoding="utf-8").splitlines()
    for line in lines[-n:]:
        print(line)
    return 0


def cmd_mode() -> int:
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    if not mode:
        print("error: mode is required  (shuffle | sequential | repeat | repeat_one)")
        return 2
    _zh_modes = {
        "随机": "shuffle", "随机播放": "shuffle",
        "顺序": "sequential", "顺序播放": "sequential",
        "单曲循环": "repeat_one", "单曲": "repeat_one",
        "列表循环": "repeat", "循环": "repeat", "循环播放": "repeat",
    }
    mode = _zh_modes.get(mode, mode)
    return _mcp_print("set_play_mode", {"mode": mode})


def cmd_help() -> int:
    G = "\x1b[1;38;2;255;230;100m"
    C = "\x1b[38;2;100;195;210m"
    W = "\x1b[38;2;200;200;230m"
    D = "\x1b[38;2;120;130;130m"
    R = "\x1b[0m"

    def sec(title: str) -> str:
        return f"{C}▸ {title}{R}"

    def row(cmd: str, desc: str, pad: int = 22) -> str:
        return f"  {W}{cmd:<{pad}}{R}{D}{desc}{R}"

    lang = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in ("en", "zh") else "en"

    if lang == "zh":
        lines = [
            f"{G}/cwb — coding-with-beat 命令速查{R}",
            "",
            sec("播放控制"),
            row("play [歌名 / song]",    "播放 / 搜索播放"),
            row("pause / 暂停",           "暂停"),
            row("next  / 下一首",         "下一首"),
            row("prev  / 上一首",         "上一首"),
            row("like  / 收藏",           "收藏当前曲目"),
            row("np    / 当前",           "显示正在播放"),
            "",
            sec("音量 & 进度"),
            row("volume <0-100>",         "音量 70  /  音量70"),
            row("seek <T>",               "跳转 1:30  /  跳至90"),
            "",
            sec("来源 & 模式"),
            row("source <来源>",          "apple_music  qq_music  local"),
            row("",                       "苹果音乐  本地  qq音乐"),
            row("mode <模式>",            "shuffle / sequential / repeat / repeat_one"),
            row("",                       "随机 / 顺序 / 循环 / 单曲循环"),
            "",
            sec("界面"),
            row("player / 播放器",        "像素播放器"),
            row("watch",                  "实时 TUI  Space/n/p/l 控制  q 退出"),
            row("karaoke",                "全屏卡拉 OK  同上快捷键"),
            row("lyrics / 歌词",          "歌词窗口"),
            row("cover [rgb|gameboy]",    "专辑封面"),
            "",
            sec("记录 & 设置"),
            row("history [n]",            "最近 n 首播放记录（默认 10）"),
            row("bar show|hide|auto",     "状态栏：始终显示 / 隐藏 / 仅播放时"),
            row("status / 状态",          "当前完整状态"),
            "",
            f"  {D}中英文均可：/cwb 暂停  /cwb 下一首  /cwb 切换苹果音乐  /cwb help{R}",
        ]
    else:
        lines = [
            f"{G}/cwb — coding-with-beat command reference{R}",
            "",
            sec("Playback"),
            row("play [query]",           "Resume or search & play"),
            row("pause",                  "Pause playback"),
            row("next",                   "Skip to next track"),
            row("prev",                   "Go to previous track"),
            row("like",                   "Like the current track"),
            row("np",                     "Show now playing"),
            "",
            sec("Volume & Position"),
            row("volume <0-100>",         "Set playback volume  (e.g. volume 70)"),
            row("seek <T>",               "Seek to position  (90  or  1:30)"),
            "",
            sec("Source & Mode"),
            row("source <name>",          "apple_music | qq_music | local"),
            row("mode <mode>",            "shuffle | sequential | repeat | repeat_one"),
            "",
            sec("UI"),
            row("player",                 "Pixel player"),
            row("watch",                  "Live TUI  Space/n/p/l to control  q to quit"),
            row("karaoke",                "Full-screen lyrics  (same shortcuts)"),
            row("lyrics",                 "Lyrics window"),
            row("cover [rgb|gameboy]",    "Album cover art"),
            "",
            sec("History & Settings"),
            row("history [n]",            "Last n played tracks (default 10)"),
            row("bar show|hide|auto",     "Statusline: always | hidden | when playing"),
            row("status",                 "Full current state"),
            "",
            f"  {D}Chinese commands also work: /cwb 暂停  /cwb 下一首  /cwb 帮助{R}",
        ]
    print("\n".join(lines))
    return 0


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

    ap = argparse.ArgumentParser(prog="cwb server")
    ap.add_argument("--host", default=os.environ.get("CWB_MCP_HOST") or os.environ.get("CC_JUKEBOX_MCP_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=_env_int("CWB_MCP_PORT", _env_int("CC_JUKEBOX_MCP_PORT", 8765)))
    ap.add_argument("--path", default=os.environ.get("CWB_MCP_PATH") or os.environ.get("CC_JUKEBOX_MCP_PATH", "/mcp"))
    ap.add_argument("--stateless", action="store_true")
    ap.add_argument("--log-level", default=os.environ.get("CWB_MCP_LOG_LEVEL") or os.environ.get("CC_JUKEBOX_MCP_LOG_LEVEL", "info"))
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
    "volume": cmd_volume,
    "seek": cmd_seek,
    "history": cmd_history,
    "bar": cmd_bar,
    "help": cmd_help,
    # ── Chinese aliases ────────────────────────────────────────────────────
    "暂停": cmd_pause,
    "下一首": cmd_next,
    "上一首": cmd_prev,
    "播放": cmd_play,
    "收藏": cmd_like,
    "歌词": cmd_lyrics,
    "播放器": cmd_player,
    "状态": cmd_status,
    "历史": cmd_history,
    "状态栏": cmd_bar,
    "音量": cmd_volume,
    "模式": cmd_mode,
    "来源": cmd_source,
    "帮助": cmd_help,
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
