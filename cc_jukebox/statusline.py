"""Render a compact single-line statusline for Claude Code.

CC invokes the configured `statusLine.command`, passes JSON context on stdin,
and renders the program's stdout as the bottom bar. We must:
  - be fast (<200ms)
  - return short ANSI-coloured text (one line, plus an optional lyric line)
  - prefer cached state, but opportunistically re-poll when stale so the bar
    stays synced after seeks/restarts/external GUI changes
"""
from __future__ import annotations

import json
import re
import sys
import time

from . import state, focus, dj
from .config import LYRICS_CACHE
from .sources import get_source
from .ui.lyrics import parse_lrc, _index_for_position
from .ui.progress import render_progress


# If our cached position sample is older than this, do a fast re-poll
# of the source before rendering. ~50–150ms for AppleScript; acceptable.
_STALE_AFTER = 2.5


def _mmss(seconds: float) -> str:
    s = max(0, int(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def _maybe_refresh(st):
    """If the position sample is stale, re-poll the active source. Returns the
    (possibly updated) state. Failures fall back to cached state silently."""
    base = st.track.position_sampled_at or st.updated_at
    if base and (time.time() - base) < _STALE_AFTER:
        return st
    try:
        src = get_source(st.source)
        np = src.now_playing()
    except Exception:
        return st
    if not np.title:
        return st
    st.track.title = np.title
    st.track.artist = np.artist
    st.track.album = np.album
    st.track.duration = np.duration
    st.track.position = np.position
    st.track.position_sampled_at = time.time()
    st.track.artwork_path = np.artwork_path
    st.track.source = np.source
    st.playing = np.playing
    try:
        state.save(st)
    except Exception:
        pass
    return st


def _live_position(st) -> float:
    """Extrapolate position from the last source sample so the bar keeps
    moving between polls."""
    pos = st.track.position
    base = st.track.position_sampled_at or st.updated_at
    if st.playing and base and st.track.duration:
        pos = min(st.track.duration, pos + (time.time() - base))
    return pos


_KEY_RE = re.compile(r"[^a-zA-Z0-9一-鿿]+")
_SOURCE_PREFIX = {"apple_music": "am", "local": "local", "qq_music": "qq"}


def _cached_lyric_line(st, pos: float):
    """Return the active LRC line for the current track, or None.
    Reads only from the on-disk cache — no network calls in the statusline."""
    t = st.track
    if not t.title:
        return None
    key = _KEY_RE.sub("_", f"{t.artist}_{t.album}_{t.title}").strip("_")[:160]
    prefix = _SOURCE_PREFIX.get(st.source, "am")
    cache = LYRICS_CACHE / f"{prefix}_{key}.txt"
    if not cache.exists():
        return None
    try:
        txt = cache.read_text(encoding="utf-8")
    except Exception:
        return None
    cues, is_lrc = parse_lrc(txt)
    if not is_lrc:
        return None
    cues = [(ts, body) for ts, body in cues if body.strip()]
    if not cues:
        return None
    idx = _index_for_position(cues, pos)
    if idx < 0:
        return None
    return cues[idx][1]


_PLAY_PULSE = ("▶", "▷")  # alternates every second when playing


def render() -> str:
    st = state.load()
    st = _maybe_refresh(st)
    f = focus.status()

    face = dj.face(st.dj_mood or "neutral")
    pos = _live_position(st)

    if st.track.title:
        title = st.track.title[:28]
        artist = (st.track.artist or "—")[:18]
        bar = render_progress(pos, st.track.duration, width=14)
        if st.playing:
            icon = _PLAY_PULSE[int(time.time()) & 1]
            icon_seq = f"\x1b[1;38;2;155;188;15m{icon}\x1b[0m"
        else:
            icon_seq = "\x1b[1;38;2;120;130;130m❚❚\x1b[0m"
        track = f"{icon_seq} \x1b[38;2;200;200;230m{title}\x1b[0m \x1b[38;2;120;130;130m— {artist}\x1b[0m {bar}"
    else:
        track = "\x1b[38;2;120;130;130mno track loaded — try /mcp call cc-jukebox play_song <name>\x1b[0m"

    focus_chip = ""
    if f.active:
        emoji = "🍅" if f.phase == "work" else "☕"
        focus_chip = f"  \x1b[38;2;255;180;120m{emoji} {f.phase} {_mmss(f.remaining)}\x1b[0m"

    vibe_chip = ""
    if st.vibe:
        vibe_chip = f"  \x1b[38;2;155;188;15m[{st.vibe}]\x1b[0m"

    line1 = f"{face}  {track}{vibe_chip}{focus_chip}"

    lyric = _cached_lyric_line(st, pos) if st.track.title else None
    if lyric:
        # Truncate so the lyric line isn't longer than the track line is wide.
        if len(lyric) > 60:
            lyric = lyric[:57] + "…"
        line2 = f"\x1b[3;38;2;180;180;200m♪ {lyric}\x1b[0m"
        return f"{line1}\n{line2}"
    return line1


def main() -> int:
    try:
        _ = sys.stdin.read()  # CC sends context JSON; we don't currently need it
    except Exception:
        pass
    sys.stdout.write(render())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
