"""MCP server: exposes CC-Jukebox tools to Claude Code.

Run with:
    python -m cc_jukebox.server
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


mcp = FastMCP("cc-jukebox")


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


@mcp.tool()
def now_playing() -> str:
    """Return the currently playing track from the active source.
    Output: a short text block with title, artist, album, position, source.
    Use this whenever the user asks 'what's playing' or before deciding to
    skip/replay."""
    st, np = _refresh_now_playing()
    if not np.title:
        return f"(nothing playing — source: {st.source})"
    return (
        f"♪ {np.title}\n"
        f"  by {np.artist or '—'} · {np.album or '—'}\n"
        f"  {int(np.position):>4}s / {int(np.duration):>4}s  source={np.source}  {'▶ playing' if np.playing else '❚❚ paused'}"
    )


@mcp.tool()
def play() -> str:
    """Resume playback on the active source."""
    st = state.load()
    get_source(st.source).play()
    _refresh_now_playing()
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
    _refresh_now_playing()
    return "⏭ next"


@mcp.tool()
def prev_track() -> str:
    """Go to the previous track."""
    st = state.load()
    get_source(st.source).prev()
    _refresh_now_playing()
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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
