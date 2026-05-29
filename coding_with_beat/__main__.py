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
    pet          — launch the desktop pet; defaults to Petdex boba, use --builtin for built-in pixels
    source [name] — print or set source (apple_music | local | qq_music)
    karaoke      — full-screen centred lyrics from the MCP server (Ctrl-C to exit)
    play [query] — resume current track, or search & play if a query is given
    play <n>     — play track #n from the last search or list results
    search <q>   — search library + Apple Music catalog and show numbered results
    list [n]     — list all library tracks (default 100)
    loved [n]    — list all loved/hearted tracks (default 50)
    search_loved <q> — search only within loved tracks
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
    restart      — restart the background MCP server
    help         — show command reference
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


def _env_first(name: str, legacy_name: str, default: str) -> str:
    return os.environ.get(name) or os.environ.get(legacy_name) or default


_MCP_ERROR_PREFIXES = ("(unsupported", "(no match")
_MCP_ERROR_MARKERS = ("full playback did not start",)
DEFAULT_PETDEX_SLUG = "boba"


def _mcp_print(tool: str, kwargs: dict | None = None) -> int:
    from .mcp_client import MCPClientError, call_tool

    try:
        output = call_tool(tool, kwargs or {})
    except MCPClientError as e:
        print(str(e), file=sys.stderr)
        return 1
    if output:
        print(output)
    if output and (
        any(output.startswith(p) for p in _MCP_ERROR_PREFIXES) or any(marker in output for marker in _MCP_ERROR_MARKERS)
    ):
        return 1
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
    from . import dj, state
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


def cmd_pet() -> int:
    try:
        from .pet.app import run
        from .pet.settings import load_settings

        args = sys.argv[2:]
        petdex_slug = load_settings().petdex_slug or DEFAULT_PETDEX_SLUG
        if "--builtin" in args:
            petdex_slug = None
        if "--petdex" in sys.argv[2:]:
            idx = sys.argv.index("--petdex")
            if idx + 1 >= len(sys.argv):
                print("error: usage: cwb pet --petdex <slug>", file=sys.stderr)
                return 2
            petdex_slug = sys.argv[idx + 1]
        return run(petdex_slug=petdex_slug, hide_dock="--show-dock" not in args)
    except RuntimeError as e:
        if "PySide6" in str(e):
            print(
                "cwb pet requires the optional desktop dependency.\n"
                "Install it with: pip install 'coding-with-beat[pet]'",
                file=sys.stderr,
            )
            return 1
        print(str(e), file=sys.stderr)
        return 1


def cmd_source() -> int:
    if len(sys.argv) < 3:
        return _mcp_print("current_source")
    name = sys.argv[2]
    return _mcp_print("set_source", {"name": name})


def cmd_karaoke() -> int:
    from .karaoke import run

    width = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    return run(width=width)


def cmd_list() -> int:
    """list [n] — show all library tracks (default 100)."""
    limit = 100
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            pass
    return _mcp_print("list_library", {"limit": limit})


def cmd_loved() -> int:
    """loved [n] — list all loved/hearted tracks (default 50)."""
    limit = 50
    if len(sys.argv) > 2:
        try:
            limit = int(sys.argv[2])
        except ValueError:
            pass
    return _mcp_print("list_loved", {"limit": limit})


def cmd_playlists() -> int:
    """playlists — list all user playlists (user-created + subscription)."""
    return _mcp_print("list_playlists", {})


def cmd_play_playlist() -> int:
    """play_playlist <name> — play a playlist by name."""
    name = " ".join(sys.argv[2:]).strip()
    if not name:
        print("error: usage: play_playlist <playlist name>")
        return 2
    return _mcp_print("play_playlist", {"name": name})


def cmd_tips() -> int:
    """tips — show a card of natural-language phrases you can say."""
    return _mcp_print("tips")


def cmd_search_loved() -> int:
    """search_loved <query> — search within loved tracks only."""
    query = " ".join(sys.argv[2:]).strip()
    if not query:
        print("error: usage: search_loved <query>")
        return 2
    return _mcp_print("search_loved", {"query": query})


def cmd_search() -> int:
    """search <query> — list matching tracks from library and Apple Music catalog."""
    query = " ".join(sys.argv[2:]).strip()
    if not query:
        print("error: usage: search <query>")
        return 2
    return _mcp_print("search", {"query": query})


def cmd_smart_search() -> int:
    """smart_search <description> | <q1> -- <q2> -- <q3> — find tracks by mood/scene/vibe."""
    import asyncio

    raw = sys.argv[2:]
    if not raw:
        print("error: usage: smart_search <description>  OR  smart_search <q1> -- <q2> -- <q3>")
        return 2

    # Split on "--" to detect multi-angle mode
    queries: list[str] = []
    current: list[str] = []
    for arg in raw:
        if arg == "--":
            if current:
                queries.append(" ".join(current).strip())
            current = []
        else:
            current.append(arg)
    if current:
        queries.append(" ".join(current).strip())
    queries = [q for q in queries if q]

    from .server import _multi_angle_search, _write_active_mode, _write_queue_file
    from .sources import get_source

    if len(queries) > 1:
        print(f"🔍 多角度搜索: {len(queries)} 个方向", flush=True)
        result = asyncio.run(_multi_angle_search(queries))
        print(result)
        return 0

    # Single-angle (backwards compat)
    query = queries[0]
    print(f"🔍 理解描述: {query}", flush=True)

    import threading

    am_hits: list = []
    local_hits: list = []

    def _search_am() -> None:
        nonlocal am_hits
        print("🎵 搜索 Apple Music...", flush=True)
        am_hits = get_source("apple_music").search(query, 8) or []

    def _search_local() -> None:
        nonlocal local_hits
        print("📁 搜索本地文件...", flush=True)
        local_hits = get_source("local").search(query, 8) or []

    t1 = threading.Thread(target=_search_am, daemon=True)
    t2 = threading.Thread(target=_search_local, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    seen: set[str] = set()
    merged: list[dict] = []
    for h in am_hits + local_hits:
        key = f"{h.get('title', '').lower()}|{h.get('artist', '').lower()}"
        if key not in seen:
            seen.add(key)
            merged.append(h)

    if not merged:
        print(f"(no matches for '{query}')")
        return 1

    print(f"✅ 找到 {len(merged)} 首\n", flush=True)

    _write_queue_file("search", {"tracks": merged, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")

    has_catalog = False
    lines = []
    for i, h in enumerate(merged):
        src = h.get("source", "")
        if src == "library":
            tag = " [资料库]"
        elif src == "apple_music":
            tag = " [Apple Music]"
            has_catalog = True
        elif src == "local":
            tag = " [本地]"
        else:
            tag = ""
        lines.append(f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{tag}")
    if has_catalog:
        lines.append(
            "\n💡 [Apple Music] 曲目需要先添加到资料库才能播放。如果想直接播放已下载的歌曲，跟我说「打开资料库」就行。"
        )
    print("\n".join(lines))
    return 0


def cmd_play() -> int:
    """play [query] — resume if no query, otherwise search and play."""
    query = " ".join(sys.argv[2:]).strip()
    if query:
        if query.isdigit():
            return _mcp_print("play_number", {"number": int(query)})
        return _mcp_print("play_song", {"query": query})
    return _mcp_print("play")


def cmd_resume() -> int:
    """resume — re-search and play the last known track from its saved position."""
    return _mcp_print("resume")


def cmd_play_number() -> int:
    """play_number <n> — play track #n from the last search or list results."""
    if len(sys.argv) < 3:
        print("error: usage: play_number <n>")
        return 2
    try:
        n = int(sys.argv[2])
    except ValueError:
        print("error: argument must be a positive integer")
        return 2
    return _mcp_print("play_number", {"number": n})


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


def cmd_profile() -> int:
    from . import profile as _profile

    args = sys.argv[2:]
    html_now = "--html" in args  # skip prompt, go straight to HTML
    period_args = [a for a in args if not a.startswith("-")]

    valid = {"daily", "weekly", "monthly", "yearly"}
    period = period_args[0] if period_args else "weekly"
    if period not in valid:
        print(f"error: period must be one of: {', '.join(sorted(valid))}")
        return 2

    try:
        prof = _profile.build_profile(period)
    except ValueError:
        print("（听歌记录不足 5 首，多听一会儿再来生成报告吧 🎵）")
        return 0

    # Always print the text report first
    print(_profile.build_report(prof))
    print()
    queries = _profile.build_recommendation_queries(prof)
    if queries:
        print("🎵 个性化推荐 queries：")
        for i, q in enumerate(queries, 1):
            print(f"  {i}. {q}")

    # Prompt for HTML unless --html was passed directly
    if not html_now:
        try:
            answer = input("\n需要生成 HTML 报告并在浏览器打开吗？[y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = ""
        if answer not in ("y", "yes", "是", "需要"):
            return 0

    import subprocess

    from .config import DATA_DIR

    html = _profile.build_html_report(prof)
    out_path = DATA_DIR / f"report_{period}_{prof['generated_at'].strftime('%Y%m%d')}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    print(f"报告已生成：{out_path}")
    subprocess.run(["open", str(out_path)], check=False)
    return 0


def cmd_mode() -> int:
    mode = sys.argv[2] if len(sys.argv) > 2 else ""
    if not mode:
        print("error: mode is required  (shuffle | sequential | repeat | repeat_one)")
        return 2
    _zh_modes = {
        "随机": "shuffle",
        "随机播放": "shuffle",
        "顺序": "sequential",
        "顺序播放": "sequential",
        "单曲循环": "repeat_one",
        "单曲": "repeat_one",
        "列表循环": "repeat",
        "循环": "repeat",
        "循环播放": "repeat",
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
            row("play [歌名 / song]", "播放 / 搜索播放"),
            row("play <序号>", "按编号播放（来自搜索或列表结果）"),
            row("search <关键词>", "搜索资料库 + Apple Music 目录"),
            row("list [n]", "列出资料库所有歌曲（默认100首）"),
            row("loved [n]", "列出喜欢列表（默认50首）"),
            row("search_loved <q>", "在喜欢列表里搜索"),
            row("playlists", "列出所有歌单"),
            row("play_playlist <名称>", "播放指定歌单"),
            row("pause / 暂停", "暂停"),
            row("next  / 下一首", "下一首"),
            row("prev  / 上一首", "上一首"),
            row("like  / 收藏", "收藏当前曲目"),
            row("np    / 当前", "显示正在播放"),
            "",
            sec("音量 & 进度"),
            row("volume <0-100>", "音量 70  /  音量70"),
            row("seek <T>", "跳转 1:30  /  跳至90"),
            "",
            sec("来源 & 模式"),
            row("source <来源>", "apple_music  qq_music  local"),
            row("", "苹果音乐  本地  qq音乐"),
            row("mode <模式>", "shuffle / sequential / repeat / repeat_one"),
            row("", "随机 / 顺序 / 循环 / 单曲循环"),
            "",
            sec("界面"),
            row("player / 播放器", "像素播放器"),
            row("watch", "实时 TUI  Space/n/p/l 控制  q 退出"),
            row("karaoke", "全屏卡拉 OK  同上快捷键"),
            row("lyrics / 歌词", "歌词窗口"),
            row("cover [rgb|gameboy]", "专辑封面"),
            "",
            sec("记录 & 设置"),
            row("history [n]", "最近 n 首播放记录（默认 10）"),
            row("bar show|hide|auto", "状态栏：始终显示 / 隐藏 / 仅播放时"),
            row("status / 状态", "当前完整状态"),
            "",
            f"  {D}中英文均可：/cwb 暂停  /cwb 下一首  /cwb 切换苹果音乐  /cwb help{R}",
        ]
    else:
        lines = [
            f"{G}/cwb — coding-with-beat command reference{R}",
            "",
            sec("Playback"),
            row("play [query]", "Resume or search & play"),
            row("play <n>", "Play track #n from last search or list"),
            row("search <query>", "Search library + Apple Music catalog"),
            row("list [n]", "List all library tracks (default 100)"),
            row("loved [n]", "List all loved/hearted tracks (default 50)"),
            row("search_loved <q>", "Search within loved tracks only"),
            row("playlists", "List all playlists (user + subscription)"),
            row("play_playlist <name>", "Play a playlist by name"),
            row("pause", "Pause playback"),
            row("next", "Skip to next track"),
            row("prev", "Go to previous track"),
            row("like", "Like the current track"),
            row("np", "Show now playing"),
            "",
            sec("Volume & Position"),
            row("volume <0-100>", "Set playback volume  (e.g. volume 70)"),
            row("seek <T>", "Seek to position  (90  or  1:30)"),
            "",
            sec("Source & Mode"),
            row("source <name>", "apple_music | qq_music | local"),
            row("mode <mode>", "shuffle | sequential | repeat | repeat_one"),
            "",
            sec("UI"),
            row("player", "Pixel player"),
            row("watch", "Live TUI  Space/n/p/l to control  q to quit"),
            row("karaoke", "Full-screen lyrics  (same shortcuts)"),
            row("lyrics", "Lyrics window"),
            row("cover [rgb|gameboy]", "Album cover art"),
            "",
            sec("History & Settings"),
            row("history [n]", "Last n played tracks (default 10)"),
            row("bar show|hide|auto", "Statusline: always | hidden | when playing"),
            row("status", "Full current state"),
            "",
            f"  {D}Tip: use search first for precise matches, then play the result number.{R}",
        ]
    print("\n".join(lines))
    return 0


def cmd_prefetch() -> int:
    """Internal: silently fetch and cache lyrics for the current track."""
    import re

    from . import state
    from .config import DATA_DIR
    from .sources import get_source

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
        key = re.sub(r"[^a-zA-Z0-9一-鿿]+", "_", f"{t.artist}_{t.album}_{t.title}").strip("_")[:160]
        prefix = {"apple_music": "am", "local": "local", "qq_music": "qq"}.get(st.source, "am")
        lock = DATA_DIR / f".lyfetch_{prefix}_{key}"
        lock.unlink(missing_ok=True)
    return 0


def _find_repo():
    """Locate the coding-with-beat git repo via multiple fallbacks."""
    import subprocess as _sp
    from pathlib import Path as _Path

    from .config import DATA_DIR

    candidates = []

    # 1. explicit repo-path file (written by install.sh)
    repo_file = DATA_DIR / "repo-path"
    if repo_file.exists():
        candidates.append(_Path(repo_file.read_text().strip()))

    # 2. bootstrap default clone location
    candidates.append(_Path.home() / ".coding-with-beat" / "src")

    # 3. editable install location from pip metadata
    try:
        r = _sp.run(
            [sys.executable, "-m", "pip", "show", "coding-with-beat"],
            capture_output=True,
            text=True,
        )
        for line in r.stdout.splitlines():
            if line.lower().startswith("editable project location:"):
                candidates.append(_Path(line.split(":", 1)[1].strip()))
                break
    except Exception:
        pass

    for p in candidates:
        if (p / ".git").exists():
            # persist for next time
            try:
                repo_file.write_text(str(p) + "\n")
            except Exception:
                pass
            return p
    return None


def cmd_update() -> int:
    """update — pull latest changes from the git repo and restart the MCP server."""
    import subprocess as _sp
    from pathlib import Path as _Path

    repo = _find_repo()
    if repo is None:
        print("error: could not find the coding-with-beat git repository.")
        print(
            "  Re-run the installer:  curl -LsSf https://raw.githubusercontent.com/jaychempan/coding-with-beat/main/bootstrap.sh | sh"
        )
        return 1
    print(f"Pulling latest changes from {repo} ...", flush=True)
    r = _sp.run(["git", "-C", str(repo), "pull"], text=True)
    if r.returncode != 0:
        print("error: git pull failed")
        return 1
    plist = _Path.home() / "Library/LaunchAgents/com.coding-with-beat.server.plist"
    if plist.exists():
        print("Restarting MCP server ...")
        _sp.run(["launchctl", "unload", str(plist)], capture_output=True)
        _sp.run(["launchctl", "load", str(plist)], capture_output=True)
        print("MCP server restarted.")
    print("coding-with-beat is up to date.")
    return 0


def cmd_restart() -> int:
    """restart — restart the background MCP server."""
    import subprocess as _sp
    from pathlib import Path as _Path

    plist = _Path.home() / "Library/LaunchAgents/com.coding-with-beat.server.plist"
    if plist.exists():
        import os

        label = "com.coding-with-beat.server"
        domain = f"gui/{os.getuid()}"
        print("Restarting MCP server via launchctl ...")
        # kickstart -k kills the running instance before starting a new one
        r = _sp.run(
            ["launchctl", "kickstart", "-k", f"{domain}/{label}"],
            capture_output=True,
        )
        if r.returncode != 0:
            # Service may not be bootstrapped yet — fall back to bootout+bootstrap
            _sp.run(["launchctl", "bootout", domain, str(plist)], capture_output=True)
            _sp.run(["launchctl", "bootstrap", domain, str(plist)], capture_output=True)
        print("MCP server restarted.")
        return 0

    # Fallback: find and kill the process, then relaunch with same args
    import os
    import signal
    import time

    r = _sp.run(["pgrep", "-f", "cwb server"], capture_output=True, text=True)
    pids = [int(p) for p in r.stdout.split() if p.strip()]
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if pids:
        time.sleep(1)

    # Re-launch with default args (same as what launchctl would use)
    log_dir = _Path.home() / ".coding-with-beat" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout = open(log_dir / "server.log", "a")
    stderr = open(log_dir / "server.err.log", "a")
    _sp.Popen(
        [sys.executable, "-m", "coding_with_beat", "server", "--host", "127.0.0.1", "--port", "8765", "--path", "/mcp"],
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )
    print("MCP server restarted.")
    return 0


def cmd_server() -> int:
    import argparse

    from .server import main

    ap = argparse.ArgumentParser(prog="cwb server")
    ap.add_argument(
        "--host",
        default=_env_first("CWB_MCP_HOST", "CC_JUKEBOX_MCP_HOST", "127.0.0.1"),
    )
    ap.add_argument(
        "--port",
        type=int,
        default=_env_int("CWB_MCP_PORT", _env_int("CC_JUKEBOX_MCP_PORT", 8765)),
    )
    ap.add_argument(
        "--path",
        default=_env_first("CWB_MCP_PATH", "CC_JUKEBOX_MCP_PATH", "/mcp"),
    )
    ap.add_argument("--stateless", action="store_true")
    ap.add_argument(
        "--log-level",
        default=_env_first("CWB_MCP_LOG_LEVEL", "CC_JUKEBOX_MCP_LOG_LEVEL", "info"),
    )
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


def cmd_codex_hook() -> int:
    from .codex_vibe import main

    return main()


COMMANDS = {
    "_prefetch": cmd_prefetch,
    "update": cmd_update,
    "restart": cmd_restart,
    "server": cmd_server,
    "statusline": cmd_statusline,
    "hook": cmd_hook,
    "codex_hook": cmd_codex_hook,
    "init": cmd_init,
    "status": cmd_status,
    "welcome": cmd_welcome,
    "demo": cmd_demo,
    "banner": cmd_banner,
    "cover": cmd_cover,
    "lyrics": cmd_lyrics,
    "player": cmd_player,
    "watch": cmd_watch,
    "pet": cmd_pet,
    "source": cmd_source,
    "karaoke": cmd_karaoke,
    "list": cmd_list,
    "loved": cmd_loved,
    "search_loved": cmd_search_loved,
    "playlists": cmd_playlists,
    "play_playlist": cmd_play_playlist,
    "tips": cmd_tips,
    "能做什么": cmd_tips,
    "search": cmd_search,
    "smart_search": cmd_smart_search,
    "play": cmd_play,
    "resume": cmd_resume,
    "play_number": cmd_play_number,
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
    "profile": cmd_profile,
    "bar": cmd_bar,
    "help": cmd_help,
    # ── Chinese aliases ────────────────────────────────────────────────────
    "继续": cmd_resume,
    "恢复": cmd_resume,
    "暂停": cmd_pause,
    "下一首": cmd_next,
    "上一首": cmd_prev,
    "播放": cmd_play,
    "搜索": cmd_search,
    "找歌": cmd_search,
    "列表": cmd_list,
    "资料库": cmd_list,
    "喜欢": cmd_loved,
    "喜欢列表": cmd_loved,
    "收藏列表": cmd_loved,
    "搜索喜欢": cmd_search_loved,
    "歌单": cmd_playlists,
    "我的歌单": cmd_playlists,
    "播放歌单": cmd_play_playlist,
    "收藏": cmd_like,
    "歌词": cmd_lyrics,
    "播放器": cmd_player,
    "桌面宠物": cmd_pet,
    "状态": cmd_status,
    "历史": cmd_history,
    "画像": cmd_profile,
    "音乐画像": cmd_profile,
    "听歌报告": cmd_profile,
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
