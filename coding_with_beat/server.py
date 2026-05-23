"""MCP server: exposes coding-with-beat tools to Claude Code.

Run with:
    python -m coding_with_beat.server
    python -m coding_with_beat server
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import dj, focus, state
from .config import DATA_DIR
from .lyrics_snapshot import current_text as current_lyrics_text
from .lyrics_snapshot import track_key
from .sources import get_source
from .ui import (
    boxed,
    render_cover,
    render_cover_gameboy,
    render_lyrics_window,
    render_progress,
    render_spectrum_color,
    retro_banner,
)

MCP_HTTP_HOST_ENV = "CWB_MCP_HOST"
MCP_HTTP_PORT_ENV = "CWB_MCP_PORT"
MCP_HTTP_PATH_ENV = "CWB_MCP_PATH"
_LEGACY_MCP_HTTP_HOST_ENV = "CC_JUKEBOX_MCP_HOST"
_LEGACY_MCP_HTTP_PORT_ENV = "CC_JUKEBOX_MCP_PORT"
_LEGACY_MCP_HTTP_PATH_ENV = "CC_JUKEBOX_MCP_PATH"
CONTROL_REFRESH_DELAY = 0.4


def _one_off_file():
    return DATA_DIR / "one_off_queue.json"


def _queue_file(name: str):
    if name not in ("library", "search"):
        raise ValueError(f"unknown queue name: {name!r}")
    return DATA_DIR / ("library_queue.json" if name == "library" else "search_queue.json")


def _load_queue_file(name: str) -> dict:
    """Load library or search queue. Returns dict with tracks, index, expected_title."""
    try:
        return json.loads(_queue_file(name).read_text(encoding="utf-8"))
    except Exception:
        return {"tracks": [], "index": 0, "expected_title": ""}


def _write_queue_file(name: str, data: dict) -> None:
    try:
        _queue_file(name).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _read_active_mode() -> dict:
    """Returns {mode, context}. Defaults to library for both."""
    try:
        return json.loads((DATA_DIR / "active_mode.json").read_text(encoding="utf-8"))
    except Exception:
        return {"mode": "library", "context": "library"}


def _write_active_mode(mode: str | None = None, context: str | None = None) -> None:
    if mode is None and context is None:
        return
    current = _read_active_mode()
    if mode is not None:
        current["mode"] = mode
    if context is not None:
        current["context"] = context
    try:
        (DATA_DIR / "active_mode.json").write_text(json.dumps(current, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _env_first(name: str, legacy_name: str, default: str) -> str:
    return os.environ.get(name) or os.environ.get(legacy_name) or default


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _normalize_path(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


mcp = FastMCP(
    "coding-with-beat",
    host=_env_first(MCP_HTTP_HOST_ENV, _LEGACY_MCP_HTTP_HOST_ENV, "127.0.0.1"),
    port=_env_int(MCP_HTTP_PORT_ENV, _env_int(_LEGACY_MCP_HTTP_PORT_ENV, 8765)),
    streamable_http_path=_normalize_path(
        _env_first(MCP_HTTP_PATH_ENV, _LEGACY_MCP_HTTP_PATH_ENV, "/mcp"),
    ),
)


def _unsupported(source: str, feature: str, reason: str) -> str:
    return f"(unsupported — source={source}, feature={feature})\n{reason}"


def _unsupported_reason(obj) -> str:
    return getattr(obj, "unsupported_reason", None) or ""


def _preview_message(np) -> str:
    return (
        f"♪ 30s preview: {np.title or '?'} — {np.artist or '—'}\n"
        "  Apple Music full playback did not start; opened/attempted the catalog track."
    )


def _needs_library_add(np) -> str:
    title = np.title or "?"
    artist = np.artist or "—"
    return (
        f'Found "{title} — {artist}" in the Apple Music catalog, but full playback did not start.\n'
        "Opened the Music.app search page. Add the track to your library, then try again.\n"
        "(Automatic catalog playback requires an active Apple Music subscription.)"
    )


def _refresh_now_playing():
    st = state.load()
    old_key = track_key(st.track.source or st.source, st.track.artist, st.track.album, st.track.title)
    src = get_source(st.source)
    np = src.now_playing()
    new_key = track_key(np.source or st.source, np.artist, np.album, np.title)
    if np.title:
        st.track.title = np.title
        st.track.artist = np.artist
        st.track.album = np.album
        st.track.duration = np.duration
        st.track.position = np.position
        if np.artwork_path:
            st.track.artwork_path = np.artwork_path
        if np.source:
            st.track.source = np.source
        if old_key != new_key:
            st.track.lyrics_key = ""
            st.track.lyrics_text = ""
            st.track.lyrics_pending = False
    st.track.position_sampled_at = time.time()
    st.playing = np.playing
    state.save(st)
    return st, np


def _refresh_after_control(delay: float = CONTROL_REFRESH_DELAY):
    if delay > 0:
        time.sleep(delay)
    return _refresh_now_playing()


def _now_playing_payload(st, np, known_lyrics_key: str = "") -> dict:
    source = np.source or st.source
    lyrics_key = track_key(source, np.artist or "", np.album or "", np.title or "")
    lyrics_text = ""
    lyrics_pending = False
    if np.title and not _unsupported_reason(np):
        lyrics_text, lyrics_pending = current_lyrics_text(
            source,
            np.artist or "",
            np.album or "",
            np.title or "",
        )
        if lyrics_key and lyrics_key == known_lyrics_key:
            lyrics_text = ""
    return {
        "source": source,
        "title": np.title or "",
        "artist": np.artist or "",
        "album": np.album or "",
        "duration": float(np.duration or 0.0),
        "position": float(np.position or 0.0),
        "playing": bool(np.playing),
        "artwork_path": np.artwork_path or "",
        "lyrics_key": lyrics_key,
        "lyrics_text": lyrics_text,
        "lyrics_pending": lyrics_pending,
        "unsupported_reason": _unsupported_reason(np),
        "sampled_at": time.time(),
    }


@mcp.tool()
def now_playing() -> str:
    """Return the currently playing track from the active source.
    Output: a short text block with title, artist, album, position, source.
    Use this whenever the user asks 'what's playing' or before deciding to
    skip/replay."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "now_playing", _unsupported_reason(np))
    if not np.title:
        return f"(nothing playing — source: {st.source})"
    return (
        f"♪ {np.title}\n"
        f"  by {np.artist or '—'} · {np.album or '—'}\n"
        f"  {int(np.position):>4}s / {int(np.duration):>4}s  source={np.source}  {'▶ playing' if np.playing else '❚❚ paused'}"
    )


def _maybe_resume_queue(np) -> None:
    """If a one-off song just ended (title changed), resume the saved queue."""
    if not _one_off_file().exists():
        return
    try:
        data = json.loads(_one_off_file().read_text(encoding="utf-8"))
    except Exception:
        _one_off_file().unlink(missing_ok=True)
        return
    one_off_title = data.get("one_off_title", "")
    resume_index = int(data.get("resume_index", 0))
    if not np.title or np.title == one_off_title:
        return  # still on the one-off song (or nothing playing yet)
    # Title changed → one-off ended; resume the queue
    _one_off_file().unlink(missing_ok=True)
    _play_queue_at(resume_index)


@mcp.tool()
def now_playing_snapshot(known_lyrics_key: str = "") -> str:
    """Return structured now-playing data as JSON for terminal integrations."""
    st, np = _refresh_now_playing()
    _maybe_resume_queue(np)
    return json.dumps(_now_playing_payload(st, np, known_lyrics_key), ensure_ascii=False)


@mcp.tool()
def current_source() -> str:
    """Return the currently selected music source name."""
    return state.load().source


@mcp.tool()
def play() -> str:
    """Resume playback on the active source."""
    st = state.load()
    get_source(st.source).play()
    _refresh_after_control()
    return "▶ play"


@mcp.tool()
def pause() -> str:
    """Pause playback on the active source."""
    st = state.load()
    get_source(st.source).pause()
    _refresh_now_playing()
    return "❚❚ paused"


@mcp.tool()
def toggle() -> str:
    """Toggle play/pause."""
    st = state.load()
    get_source(st.source).toggle()
    _refresh_now_playing()
    return "⇆ toggled"


def _read_queue_index() -> int:
    try:
        f = DATA_DIR / "queue_index.json"
        if f.exists():
            return int(json.loads(f.read_text(encoding="utf-8")).get("index", -1))
    except Exception:
        pass
    return -1


def _write_queue_index(idx: int) -> None:
    try:
        (DATA_DIR / "queue_index.json").write_text(json.dumps({"index": idx}))
    except Exception:
        pass


def _play_queue_at(idx: int, queue_name: str | None = None) -> str:
    """Play queue_name[idx]. queue_name defaults to the active mode."""
    if queue_name is None:
        queue_name = _read_active_mode().get("mode", "library")
    qdata = _load_queue_file(queue_name)
    hits = qdata.get("tracks", [])
    if not hits:
        return ""
    idx = idx % len(hits)
    hit = hits[idx]
    query = f"{hit['title']} {hit.get('artist', '')}".strip()
    st = state.load()
    src = get_source(st.source)
    np = src.play_query(query)
    _refresh_after_control()
    title = (np.title if np else None) or hit.get("title", "?")
    qdata["index"] = idx
    qdata["expected_title"] = title
    _write_queue_file(queue_name, qdata)
    _write_active_mode(mode=queue_name)
    return f"[{idx + 1}/{len(hits)}] {title}"


@mcp.tool()
def next_track() -> str:
    """Skip to the next track."""
    _one_off_file().unlink(missing_ok=True)
    results_file = DATA_DIR / "last_results.json"
    if results_file.exists():
        try:
            hits = json.loads(results_file.read_text(encoding="utf-8"))
            if hits:
                result = _play_queue_at(_read_queue_index() + 1)
                return f"⏭ next  {result}"
        except Exception:
            pass
    st = state.load()
    get_source(st.source).next()
    _refresh_after_control()
    return "⏭ next"


@mcp.tool()
def prev_track() -> str:
    """Go to the previous track."""
    _one_off_file().unlink(missing_ok=True)
    results_file = DATA_DIR / "last_results.json"
    if results_file.exists():
        try:
            hits = json.loads(results_file.read_text(encoding="utf-8"))
            if hits:
                result = _play_queue_at(_read_queue_index() - 1)
                return f"⏮ prev  {result}"
        except Exception:
            pass
    st = state.load()
    get_source(st.source).prev()
    _refresh_after_control()
    return "⏮ prev"


@mcp.tool()
def seek(seconds: float) -> str:
    """Jump to position (seconds) in the current track."""
    st = state.load()
    get_source(st.source).seek(seconds)
    _refresh_now_playing()
    return f"⇥ seek {int(seconds)}s"


@mcp.tool()
def set_volume(percent: int) -> str:
    """Set source/system volume (0-100)."""
    st = state.load()
    get_source(st.source).set_volume(percent)
    st.volume = max(0, min(100, int(percent)))
    state.save(st)
    return f"🔊 volume={st.volume}"


@mcp.tool()
def like_current() -> str:
    """Like/favorite the current track on the active source.
    Apple Music uses Music.app AppleScript. QQMusic uses macOS System Events
    menu automation. Sources that do not support this raise NotImplementedError."""
    st = state.load()
    ok = get_source(st.source).like_current()
    return f"♥ liked current track  source={st.source}" if ok else f"error: like failed  source={st.source}"


@mcp.tool()
def set_play_mode(mode: str) -> str:
    """Set play mode on the active source.
    Common modes: shuffle, sequential, repeat. Apple Music also supports
    repeat_one and repeat_all. Unsupported modes/sources raise
    NotImplementedError from the source backend."""
    st = state.load()
    ok = get_source(st.source).set_play_mode(mode)
    return f"play mode = {mode}  source={st.source}" if ok else f"error: play mode failed  source={st.source}"


@mcp.tool()
def list_library(limit: int = 100) -> str:
    """List all tracks in the library of the current source."""
    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "list_library", None)
    if not callable(fn):
        return f"(list not supported for source={st.source})"
    hits = fn(limit=limit)
    if not hits:
        return "(library is empty)"
    _write_queue_file("library", {"tracks": hits, "index": 0, "expected_title": ""})
    _write_active_mode(context="library")
    return "\n".join(
        f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}" for i, h in enumerate(hits)
    )


@mcp.tool()
def search(query: str, limit: int = 8) -> str:
    """Search the current source for tracks matching the query. Returns a
    numbered list. Use this before play_song if multiple matches are likely."""
    st = state.load()
    hits = get_source(st.source).search(query, limit=limit)
    if not hits:
        return f"(no matches for '{query}' in source={st.source})"
    _write_queue_file("search", {"tracks": hits, "index": 0, "expected_title": ""})
    _write_active_mode(context="search")
    lines = []
    for i, h in enumerate(hits):
        tag = (
            " [Library]"
            if h.get("source") == "library"
            else " [Apple Music]"
            if h.get("source") == "apple_music"
            else ""
        )
        lines.append(f"{i + 1}. {h['title']} — {h.get('artist', '?')} · {h.get('album', '?')}{tag}")
    return "\n".join(lines)


@mcp.tool()
def play_number(number: int) -> str:
    """Play a track by its 1-based index from the last search or list results."""
    am = _read_active_mode()
    context = am.get("context", "library")
    qdata = _load_queue_file(context)
    hits = qdata.get("tracks", [])
    if not hits or number < 1 or number > len(hits):
        count = len(hits) if hits else 0
        return f"(no match — #{number} out of range, last results had {count} items)"
    hit = hits[number - 1]
    query = f"{hit['title']} {hit.get('artist', '')}".strip()
    st = state.load()
    src = get_source(st.source)
    np = src.play_query(query)
    if not np:
        return f"(no match for '{query}' in source={st.source})"
    if _unsupported_reason(np) == "preview_playing":
        return _preview_message(np)
    if _unsupported_reason(np) == "needs_library_add":
        return _needs_library_add(np)
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "play_number", _unsupported_reason(np))
    if not np.title:
        return _unsupported(st.source, "play_number", "The source returned no playable track.")
    qdata["index"] = number - 1
    qdata["expected_title"] = np.title
    _write_queue_file(context, qdata)
    _write_active_mode(mode=context)
    _one_off_file().unlink(missing_ok=True)
    _refresh_now_playing()
    return f"▶ now playing: {np.title} — {np.artist or '—'}  source={np.source}"


@mcp.tool()
def play_song(query: str) -> str:
    """Search for and start playing the first match for 'query'."""
    has_queue = (DATA_DIR / "last_results.json").exists()
    st = state.load()
    src = get_source(st.source)
    np = src.play_query(query)
    if not np:
        return f"(no match for '{query}' in source={st.source})"
    if _unsupported_reason(np) == "preview_playing":
        return _preview_message(np)
    if _unsupported_reason(np) == "needs_library_add":
        return _needs_library_add(np)
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "play_song", _unsupported_reason(np))
    if not np.title:
        return _unsupported(st.source, "play_song", "The source returned no playable track.")
    if has_queue:
        # Remember where to resume after this one-off song finishes
        try:
            _one_off_file().write_text(
                json.dumps({"one_off_title": np.title, "resume_index": _read_queue_index() + 1}),
                encoding="utf-8",
            )
        except Exception:
            pass
    else:
        _one_off_file().unlink(missing_ok=True)
    _refresh_now_playing()
    return f"▶ now playing: {np.title} — {np.artist or '—'}  source={np.source}"


@mcp.tool()
def set_source(name: str) -> str:
    """Switch the active music source. name ∈ {apple_music, local, qq_music}."""
    try:
        src = get_source(name)
    except ValueError as e:
        return f"error: {e}"
    st = state.load()
    st.source = src.name
    state.save(st)
    return f"source = {src.name}"


@mcp.tool()
def show_cover(style: str = "rgb", width: int = 32, height: int = 16) -> str:
    """Render the current track's album cover as pixel ASCII.
    style: 'rgb' (true-color photo) or 'gameboy' (4-color retro)."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "show_cover", _unsupported_reason(np))
    if style == "gameboy":
        art = render_cover_gameboy(np.artwork_path, width=width, height=height)
    else:
        art = render_cover(np.artwork_path, width=width, height=height)
    return art


def _current_lyrics() -> Optional[str]:
    """Get LRC/plain lyric text from the active source, if it supports it."""
    st = state.load()
    src = get_source(st.source)
    fn = getattr(src, "lyrics", None)
    if not callable(fn):
        return None
    try:
        return fn()
    except Exception:
        return None


@mcp.tool()
def show_player(width: int = 36, with_lyrics: bool = True) -> str:
    """Render the full retro player: pixel cover + title + progress + spectrum +
    DJ Buddy sprite + (optionally) live lyrics. The 'whole experience' in one call."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "show_player", _unsupported_reason(np))
    cover = render_cover(np.artwork_path, width=width, height=int(width * 0.45))
    title = np.title or "(no track)"
    artist = np.artist or "—"
    progress = render_progress(np.position, np.duration, width=width - 2)
    spec = render_spectrum_color(np.position, width=width - 2)
    buddy = dj.sprite(st.dj_mood or "neutral")
    quip = dj.quip(st.dj_mood or "neutral")
    lines = [
        cover,
        f"\x1b[1;38;2;255;230;100m♪ {title}\x1b[0m",
        f"\x1b[38;2;180;180;200m  {artist}\x1b[0m",
        progress,
        spec,
    ]
    box_width = max(width + 4, 40)
    inner_w = box_width - 2
    if with_lyrics and np.title:
        lrc = _current_lyrics()
        if lrc:
            lines.append("\x1b[38;2;90;90;105m─── lyrics ───\x1b[0m")
            lines.append(
                render_lyrics_window(
                    lrc,
                    position=np.position,
                    duration=np.duration,
                    window=5,
                    width=inner_w,
                )
            )
    lines.append(f"\x1b[38;2;155;188;15m{buddy}\x1b[0m")
    lines.append(f'\x1b[3;38;2;200;200;230m  "{quip}"\x1b[0m')
    body = "\n".join(lines)
    return boxed(f"CWB · {st.source}", body, width=box_width)


@mcp.tool()
def show_lyrics(window: int = 7, width: int = 0) -> str:
    """Render a karaoke-style lyrics window for the currently playing track.
    Pulls timed LRC lyrics from the active source (Apple Music falls back to
    NetEase's public lyric API when AppleScript can't read catalog lyrics).
    Active line is picked by current playback position.
    width: terminal column count for wrapping (0 = auto-detect)."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "show_lyrics", _unsupported_reason(np))
    if not np.title:
        return "(no track playing)"
    lrc = _current_lyrics()
    if not lrc:
        return f"(no lyrics found for: {np.title} — {np.artist})"
    return render_lyrics_window(
        lrc,
        position=np.position,
        duration=np.duration,
        window=window,
        width=width if width > 0 else None,
    )


@mcp.tool()
def dj_say(mood: str = "") -> str:
    """DJ Buddy drops a one-liner in character. If mood is empty, uses the
    current vibe-derived mood. Useful for breaking up long debugging sessions."""
    st = state.load()
    m = mood or st.dj_mood or "neutral"
    return f"{dj.face(m)}  “{dj.quip(m)}”"


@mcp.tool()
def vibe_set(name: str) -> str:
    """Manually set the vibe (focus|build|debug|victory|fail|idle|review)."""
    st = state.load()
    st.vibe = name
    state.save(st)
    return f"vibe = {name}"


@mcp.tool()
def focus_start() -> str:
    """Start a 25/5 pomodoro loop. Status visible in statusline."""
    s = focus.start()
    return f"🍅 focus on — {s.phase} {s.remaining}s remaining"


@mcp.tool()
def focus_stop() -> str:
    """Stop the pomodoro loop."""
    focus.stop()
    return "focus off"


@mcp.tool()
def focus_status() -> str:
    """Get current focus loop status."""
    s = focus.status()
    if not s.active:
        return "focus off"
    return f"🍅 {s.phase} — {s.remaining}s remaining (cycle {s.cycle})"


@mcp.tool()
def banner() -> str:
    """Print the giant CWB retro banner. Use on SessionStart or when
    the user wants the full intro."""
    return retro_banner("a pixel companion for vibecoding")


@mcp.tool()
def session_intro() -> str:
    """One-shot greeting: banner + current state + a DJ Buddy hello."""
    st, np = _refresh_now_playing()
    parts = [retro_banner("a pixel companion for vibecoding")]
    if np.title:
        parts.append(f"\n♪ {np.title} — {np.artist}  ({st.source})")
    parts.append(f"\n{dj.face('happy')}  {dj.quip('happy')}")
    return "\n".join(parts)


@mcp.tool()
def status() -> str:
    """Return a human-readable coding-with-beat status block."""
    st, np = _refresh_now_playing()
    f = focus.status()
    lines = [
        f"source : {st.source}",
        f"vibe   : {st.vibe}  (mood={st.dj_mood})",
        "focus  : " + (f"{f.phase} — {f.remaining}s left" if f.active else "off"),
    ]
    if _unsupported_reason(np):
        lines.append(f"track  : {_unsupported(np.source or st.source, 'now_playing', _unsupported_reason(np))}")
    elif np.title:
        lines.append(f"track  : {np.title} — {np.artist}")
        lines.append(f"         {int(np.position)}s / {int(np.duration)}s " + ("▶" if np.playing else "❚❚"))
    else:
        lines.append("track  : (none)")
    return "\n".join(lines)


def main(
    host: str | None = None,
    port: int | None = None,
    path: str | None = None,
    stateless_http: bool | None = None,
    log_level: str | None = None,
) -> None:
    if host is not None:
        mcp.settings.host = host
    if port is not None:
        mcp.settings.port = int(port)
    if path is not None:
        mcp.settings.streamable_http_path = _normalize_path(path)
    if stateless_http is not None:
        mcp.settings.stateless_http = stateless_http
    if log_level is not None:
        mcp.settings.log_level = log_level.upper()
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
