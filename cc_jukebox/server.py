"""MCP server: exposes CC-Jukebox tools to Claude Code.

Run with:
    python -m cc_jukebox.server
    python -m cc_jukebox server
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP

from . import dj, focus, state, vibe
from .sources import get_source
from .ui import (
    boxed, render_cover, render_cover_gameboy,
    render_progress, render_spectrum, render_spectrum_color,
    retro_banner, render_lyrics_window,
)


MCP_HTTP_HOST_ENV = "CC_JUKEBOX_MCP_HOST"
MCP_HTTP_PORT_ENV = "CC_JUKEBOX_MCP_PORT"
MCP_HTTP_PATH_ENV = "CC_JUKEBOX_MCP_PATH"
CONTROL_REFRESH_DELAY = 0.4


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
    "cc-jukebox",
    host=os.environ.get(MCP_HTTP_HOST_ENV, "127.0.0.1"),
    port=_env_int(MCP_HTTP_PORT_ENV, 8765),
    streamable_http_path=_normalize_path(os.environ.get(MCP_HTTP_PATH_ENV, "/mcp")),
)


def _unsupported(source: str, feature: str, reason: str) -> str:
    return f"(unsupported — source={source}, feature={feature})\n{reason}"


def _unsupported_reason(obj) -> str:
    return getattr(obj, "unsupported_reason", None) or ""


def _refresh_now_playing():
    st = state.load()
    src = get_source(st.source)
    np = src.now_playing()
    st.track.title = np.title
    st.track.artist = np.artist
    st.track.album = np.album
    st.track.duration = np.duration
    st.track.position = np.position
    st.track.position_sampled_at = time.time()
    st.track.artwork_path = np.artwork_path
    st.track.source = np.source
    st.playing = np.playing
    state.save(st)
    return st, np


def _refresh_after_control(delay: float = CONTROL_REFRESH_DELAY):
    if delay > 0:
        time.sleep(delay)
    return _refresh_now_playing()


def _now_playing_payload(st, np) -> dict:
    return {
        "source": np.source or st.source,
        "title": np.title or "",
        "artist": np.artist or "",
        "album": np.album or "",
        "duration": float(np.duration or 0.0),
        "position": float(np.position or 0.0),
        "playing": bool(np.playing),
        "artwork_path": np.artwork_path or "",
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


@mcp.tool()
def now_playing_snapshot() -> str:
    """Return structured now-playing data as JSON for terminal integrations."""
    st, np = _refresh_now_playing()
    return json.dumps(_now_playing_payload(st, np), ensure_ascii=False)


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


@mcp.tool()
def next_track() -> str:
    """Skip to the next track."""
    st = state.load()
    get_source(st.source).next()
    _refresh_after_control()
    return "⏭ next"


@mcp.tool()
def prev_track() -> str:
    """Go to the previous track."""
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
def search(query: str, limit: int = 8) -> str:
    """Search the current source for tracks matching the query. Returns a
    numbered list. Use this before play_song if multiple matches are likely."""
    st = state.load()
    hits = get_source(st.source).search(query, limit=limit)
    if not hits:
        return f"(no matches for '{query}' in source={st.source})"
    return "\n".join(
        f"{i+1}. {h['title']} — {h.get('artist','?')} · {h.get('album','?')}"
        for i, h in enumerate(hits)
    )


@mcp.tool()
def play_song(query: str) -> str:
    """Search for and start playing the first match for 'query'."""
    st = state.load()
    src = get_source(st.source)
    np = src.play_query(query)
    if not np:
        return f"(no match for '{query}' in source={st.source})"
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "play_song", _unsupported_reason(np))
    if not np.title:
        return _unsupported(st.source, "play_song", "The source returned no playable track.")
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
    if with_lyrics and np.title:
        lrc = _current_lyrics()
        if lrc:
            lines.append("\x1b[38;2;90;90;105m─── lyrics ───\x1b[0m")
            lines.append(render_lyrics_window(
                lrc, position=np.position, duration=np.duration, window=5
            ))
    lines.append(f"\x1b[38;2;155;188;15m{buddy}\x1b[0m")
    lines.append(f"\x1b[3;38;2;200;200;230m  “{quip}”\x1b[0m")
    body = "\n".join(lines)
    return boxed(f"CC-JUKEBOX · {st.source}", body, width=max(width + 4, 40))


@mcp.tool()
def show_lyrics(window: int = 7) -> str:
    """Render a karaoke-style lyrics window for the currently playing track.
    Pulls timed LRC lyrics from the active source (Apple Music falls back to
    NetEase's public lyric API when AppleScript can't read catalog lyrics).
    Active line is picked by current playback position."""
    st, np = _refresh_now_playing()
    if _unsupported_reason(np):
        return _unsupported(np.source or st.source, "show_lyrics", _unsupported_reason(np))
    if not np.title:
        return "(no track playing)"
    lrc = _current_lyrics()
    if not lrc:
        return f"(no lyrics found for: {np.title} — {np.artist})"
    return render_lyrics_window(
        lrc, position=np.position, duration=np.duration, window=window
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
    """Print the giant CC-JUKEBOX retro banner. Use on SessionStart or when
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
    """Return a human-readable cc-jukebox status block."""
    st, np = _refresh_now_playing()
    f = focus.status()
    lines = [
        f"source : {st.source}",
        f"vibe   : {st.vibe}  (mood={st.dj_mood})",
        "focus  : "
        + (f"{f.phase} — {f.remaining}s left" if f.active else "off"),
    ]
    if _unsupported_reason(np):
        lines.append(f"track  : {_unsupported(np.source or st.source, 'now_playing', _unsupported_reason(np))}")
    elif np.title:
        lines.append(f"track  : {np.title} — {np.artist}")
        lines.append(
            f"         {int(np.position)}s / {int(np.duration)}s "
            + ("▶" if np.playing else "❚❚")
        )
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
