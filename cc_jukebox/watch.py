"""Real-time watch mode: a continuously-redrawing player panel.

Run in a side terminal pane (or tmux window):

    python -m cc_jukebox watch

The statusline already interpolates position between MCP refreshes — but
the statusline itself only redraws on Claude Code events. This mode owns
a terminal and ticks at ~5 Hz so the progress bar and active lyric line
move smoothly in real time. Source state is polled less often (default
1 s) to keep AppleScript out of the hot path.
"""
from __future__ import annotations

import signal
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

from . import dj, state
from .sources import get_source
from .sources.base import NowPlaying
from .ui import (
    boxed,
    render_cover,
    render_hud_chip,
    render_led_time,
    render_lyrics_wave,
    render_progress,
    render_spectrum_color,
)


FRAME_HZ = 5.0
POLL_EVERY = 1.0  # seconds between AppleScript syncs
DEFAULT_WIDTH = 44


@dataclass
class _Cache:
    np: Optional[NowPlaying] = None
    lyrics: Optional[str] = None
    last_poll: float = 0.0
    last_track_key: str = ""
    poll_pos: float = 0.0           # position at the moment of the last poll
    poll_wallclock: float = 0.0     # wall clock at the moment of the last poll


def _track_key(np: NowPlaying) -> str:
    return f"{np.title}\x1f{np.artist}\x1f{np.album}"


def _poll(src, cache: _Cache) -> None:
    """Refresh from source: now_playing + lyrics (if track changed)."""
    try:
        np = src.now_playing()
    except Exception:
        return
    cache.np = np
    cache.last_poll = time.time()
    cache.poll_pos = np.position
    cache.poll_wallclock = time.time()
    key = _track_key(np)
    if key != cache.last_track_key:
        cache.last_track_key = key
        fn = getattr(src, "lyrics", None)
        if callable(fn) and np.title:
            try:
                cache.lyrics = fn()
            except Exception:
                cache.lyrics = None
        else:
            cache.lyrics = None
    # Mirror into state.json so the statusline benefits too.
    st = state.load()
    st.source = src.name
    st.track.title = np.title
    st.track.artist = np.artist
    st.track.album = np.album
    st.track.duration = np.duration
    st.track.position = np.position
    st.track.artwork_path = np.artwork_path
    st.track.source = np.source
    st.playing = np.playing
    state.save(st)


def _interpolated_position(cache: _Cache) -> float:
    if not cache.np:
        return 0.0
    if not cache.np.playing:
        return cache.poll_pos
    elapsed = time.time() - cache.poll_wallclock
    return min(cache.np.duration or 0, cache.poll_pos + elapsed)


def _render_frame(cache: _Cache, width: int) -> str:
    if not cache.np or not cache.np.title:
        return boxed(
            "CC-JUKEBOX · watch",
            "\x1b[38;2;120;130;130m(no track playing)\x1b[0m",
            width=width,
        )
    np = cache.np
    pos = _interpolated_position(cache)
    t = time.time()
    st = state.load()

    cover = render_cover(np.artwork_path, width=width - 6, height=int((width - 6) * 0.45))

    title = np.title[:width - 6]
    artist = (np.artist or "—")[:width - 6]
    play_icon = ("▶", "▷")[int(t * 2) & 1] if np.playing else "❚❚"

    hud = render_hud_chip(_track_key(np), vibe=st.vibe or "build", playing=np.playing)
    led = render_led_time(pos)
    total = f"\x1b[38;2;100;100;120m / {int(np.duration)//60:02d}:{int(np.duration)%60:02d}\x1b[0m"
    progress = render_progress(pos, np.duration, width=width - 6)
    spec = render_spectrum_color(pos, width=width - 6, t=t)

    blocks = [
        cover,
        f"\x1b[1;38;2;255;230;100m{play_icon} {title}\x1b[0m",
        f"\x1b[38;2;180;180;200m  {artist}\x1b[0m",
        hud,
        led + f"  {total}",
        progress,
        spec,
    ]

    if cache.lyrics:
        blocks.append("\x1b[38;2;90;90;105m─── lyrics ───\x1b[0m")
        blocks.append(render_lyrics_wave(
            cache.lyrics, position=pos, duration=np.duration, window=5, t=t
        ))
    else:
        blocks.append("\x1b[38;2;120;130;130m  (no lyrics for this track)\x1b[0m")

    mood = st.dj_mood or ("groove" if np.playing else "neutral")
    blocks.append(f"\x1b[38;2;155;188;15m{dj.sprite(mood)}\x1b[0m")

    return boxed(
        f"CC-JUKEBOX · {np.source} · LIVE",
        "\n".join(blocks),
        width=width,
    )


_HIDE_CURSOR = "\x1b[?25l"
_SHOW_CURSOR = "\x1b[?25h"
_ENTER_ALT  = "\x1b[?1049h"
_EXIT_ALT   = "\x1b[?1049l"
_HOME       = "\x1b[H"
_CLEAR      = "\x1b[2J"


def run(width: int = DEFAULT_WIDTH) -> int:
    cache = _Cache()
    st = state.load()
    src = get_source(st.source)
    _poll(src, cache)

    sys.stdout.write(_ENTER_ALT + _HIDE_CURSOR + _CLEAR)
    sys.stdout.flush()

    def _restore(*_):
        sys.stdout.write(_SHOW_CURSOR + _EXIT_ALT)
        sys.stdout.flush()
        sys.exit(0)

    signal.signal(signal.SIGINT, _restore)
    signal.signal(signal.SIGTERM, _restore)

    interval = 1.0 / FRAME_HZ
    try:
        while True:
            if time.time() - cache.last_poll >= POLL_EVERY:
                _poll(src, cache)
            frame = _render_frame(cache, width)
            sys.stdout.write(_HOME + frame + "\n")
            sys.stdout.flush()
            time.sleep(interval)
    finally:
        sys.stdout.write(_SHOW_CURSOR + _EXIT_ALT)
        sys.stdout.flush()
    return 0
