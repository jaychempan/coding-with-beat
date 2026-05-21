"""coding-with-beat CLI.

Usage:
    python -m coding_with_beat <command>

Commands:
    server       — start the MCP server (used by CC)
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
    karaoke      — full-screen centred lyrics with wave animation (Ctrl-C to exit)
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

import json
import os
import sys
from pathlib import Path


def _unsupported(source: str, feature: str, reason: str) -> str:
    return f"(unsupported — source={source}, feature={feature})\n{reason}"


def _unsupported_reason(obj) -> str:
    return getattr(obj, "unsupported_reason", None) or ""


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
    from . import state, focus
    from .sources import get_source
    st = state.load()
    f = focus.status()
    print(f"source : {st.source}")
    print(f"vibe   : {st.vibe}  (mood={st.dj_mood})")
    print(f"focus  : {f.phase if f.active else 'off'}"
          + (f" — {f.remaining}s left" if f.active else ""))
    try:
        np = get_source(st.source).now_playing()
    except Exception:
        np = None
    if np is not None and _unsupported_reason(np):
        print(f"track  : {_unsupported(np.source or st.source, 'now_playing', _unsupported_reason(np))}")
        return 2
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
    print(boxed(f"CWB · {st.source}", body, width=40))
    return 0


def cmd_banner() -> int:
    from .ui import retro_banner
    print(retro_banner("a pixel companion for vibecoding"))
    return 0


def cmd_welcome() -> int:
    from .ui.frame import welcome_screen
    print(welcome_screen())
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
    if _unsupported_reason(np):
        print(_unsupported(np.source or st.source, "lyrics", _unsupported_reason(np)))
        return 2
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
    if _unsupported_reason(np):
        print(_unsupported(np.source or st.source, "player", _unsupported_reason(np)))
        return 2

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
                text, position=np.position, duration=np.duration, window=5,
                width=width - 4,
            ))

    blocks.append(f"\x1b[38;2;155;188;15m{dj.sprite(st.dj_mood or 'neutral')}\x1b[0m")
    blocks.append(f"\x1b[3;38;2;200;200;230m  “{dj.quip(st.dj_mood or 'neutral')}”\x1b[0m")
    print(boxed(f"CWB · {st.source}", "\n".join(blocks), width=max(width + 4, 44)))
    return 0


def cmd_watch() -> int:
    from .watch import run
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 44
    return run(width=width)


def cmd_source() -> int:
    from . import state
    from .sources import get_source
    st = state.load()
    if len(sys.argv) < 3:
        print(st.source)
        return 0
    name = sys.argv[2]
    try:
        src = get_source(name)
    except ValueError as e:
        print(f"error: {e}")
        return 2
    st.source = src.name
    state.save(st)
    print(f"source = {src.name}")
    return 0


def cmd_karaoke() -> int:
    from .karaoke import run
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    return run(width=width)


def _print_np(np) -> int:
    if np and _unsupported_reason(np):
        print(_unsupported(getattr(np, "source", "") or "unknown", "now_playing", _unsupported_reason(np)))
        return 2
    if np and getattr(np, "title", None):
        print(f"{np.title} — {np.artist or '?'}")
        return 0
    print("(no track)")
    return 1


def _print_control_result(action: str, source_name: str, np) -> int:
    if np and _unsupported_reason(np):
        print(f"{action} sent  source={source_name}  (now-playing unsupported)")
        return 0
    return _print_np(np)


def cmd_play() -> int:
    """play [query] — resume if no query, otherwise search and play."""
    from . import state
    from .sources import get_source
    import time
    src = get_source(state.load().source)
    query = " ".join(sys.argv[2:]).strip()
    if query:
        np = src.play_query(query)
        if np and _unsupported_reason(np):
            print(_unsupported(np.source or src.name, "play", _unsupported_reason(np)))
            return 2
    else:
        src.play()
        time.sleep(0.4)
        np = src.now_playing()
        return _print_control_result("play", src.name, np)
    return _print_np(np)


def cmd_pause() -> int:
    from . import state
    from .sources import get_source
    src = get_source(state.load().source)
    src.pause()
    np = src.now_playing()
    return _print_control_result("pause", src.name, np)


def cmd_next() -> int:
    from . import state
    from .sources import get_source
    import time
    src = get_source(state.load().source)
    src.next()
    time.sleep(0.4)  # Apple Music needs a tick before now_playing reflects the new track
    return _print_control_result("next", src.name, src.now_playing())


def cmd_prev() -> int:
    from . import state
    from .sources import get_source
    import time
    src = get_source(state.load().source)
    src.prev()
    time.sleep(0.4)
    return _print_control_result("prev", src.name, src.now_playing())


def cmd_np() -> int:
    from . import state
    from .sources import get_source
    src = get_source(state.load().source)
    return _print_np(src.now_playing())


def cmd_like() -> int:
    from . import state
    from .sources import get_source
    src = get_source(state.load().source)
    try:
        ok = src.like_current()
    except NotImplementedError as e:
        print(f"not implemented: {e}")
        return 2
    print(f"liked  source={src.name}" if ok else f"error: like failed  source={src.name}")
    return 0 if ok else 1


def cmd_volume() -> int:
    from . import state
    from .sources import get_source
    if len(sys.argv) < 3:
        print("error: usage: volume <0-100>")
        return 2
    try:
        vol = int(sys.argv[2])
    except ValueError:
        print("error: volume must be an integer 0-100")
        return 2
    vol = max(0, min(100, vol))
    src = get_source(state.load().source)
    try:
        src.set_volume(vol)
    except NotImplementedError as e:
        print(f"not implemented: {e}")
        return 2
    print(f"volume = {vol}%  source={src.name}")
    return 0


def cmd_seek() -> int:
    from . import state
    from .sources import get_source
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
    src = get_source(state.load().source)
    try:
        src.seek(seconds)
    except NotImplementedError as e:
        print(f"not implemented: {e}")
        return 2
    m, s = divmod(int(seconds), 60)
    print(f"seeked to {m:02d}:{s:02d}  source={src.name}")
    return 0


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
    from . import state
    from .sources import get_source
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
    src = get_source(state.load().source)
    try:
        ok = src.set_play_mode(mode)
    except NotImplementedError as e:
        print(f"not implemented: {e}")
        return 2
    print(f"mode = {mode}  source={src.name}" if ok else f"error: mode failed  source={src.name}")
    return 0 if ok else 1


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
