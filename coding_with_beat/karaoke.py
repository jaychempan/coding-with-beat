"""Full-screen karaoke lyrics mode.

    coding-with-beat karaoke [width]

Displays the current lyric line large and centred, with ±3 context lines faded
above/below. The active line has a per-character wave animation and a white
flash on entry. The spectrum and progress bar anchor the bottom.

Ctrl-C to exit.
"""
from __future__ import annotations

import math
import signal
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import state
from .state import write_history
from .sources import get_source
from .sources.base import NowPlaying
from .ui.frame import _strip_ansi
from .ui.lyrics import parse_lrc, _index_for_position, _display_width
from .ui.progress import render_progress, render_spectrum_color


FRAME_HZ = 8.0
POLL_EVERY = 1.0

# Faded colours for context lines at distance 1, 2, 3+
_FADE = [
    (180, 170, 210),
    (120, 115, 145),
    (70, 65, 90),
]


@dataclass
class _Cache:
    np: Optional[NowPlaying] = None
    lyrics: Optional[str] = None
    cues: List[Tuple[float, str]] = field(default_factory=list)
    is_lrc: bool = False
    plain_lines: List[str] = field(default_factory=list)
    last_poll: float = 0.0
    last_track_key: str = ""
    poll_pos: float = 0.0
    poll_wallclock: float = 0.0
    last_idx: int = -2
    last_change_t: float = 0.0


def _poll(src, cache: _Cache) -> None:
    try:
        np = src.now_playing()
    except Exception:
        return
    now = time.time()
    cache.np = np
    cache.last_poll = now
    cache.poll_pos = np.position
    cache.poll_wallclock = now
    key = f"{np.title}\x1f{np.artist}"
    if key != cache.last_track_key:
        cache.last_track_key = key
        write_history(np.title, np.artist, "")
        fn = getattr(src, "lyrics", None)
        txt: Optional[str] = None
        if callable(fn) and np.title:
            try:
                txt = fn()
            except Exception:
                pass
        cache.lyrics = txt
        if txt:
            cache.cues, cache.is_lrc = parse_lrc(txt)
            cache.cues = [(ts, b) for ts, b in cache.cues if b.strip()]
            cache.plain_lines = [l.strip() for l in txt.splitlines() if l.strip()]
        else:
            cache.cues, cache.is_lrc = [], False
            cache.plain_lines = []
        cache.last_idx = -2


def _live_pos(cache: _Cache) -> float:
    if not cache.np:
        return 0.0
    if not cache.np.playing:
        return cache.poll_pos
    return min(cache.np.duration or 0, cache.poll_pos + (time.time() - cache.poll_wallclock))


def _wave_line(line: str, t: float, flash: float = 0.0) -> str:
    out = []
    for i, ch in enumerate(line):
        v = (math.sin(t * 4.0 + i * 0.45) + 1) / 2
        wv_r, wv_g, wv_b = 255, int(230 + v * 25), int(100 + v * 130)
        if flash > 0:
            r = int(wv_r + flash * (255 - wv_r))
            g = int(wv_g + flash * (255 - wv_g))
            b = int(wv_b + flash * (255 - wv_b))
        else:
            r, g, b = wv_r, wv_g, wv_b
        out.append(f"\x1b[1;38;2;{r};{g};{b}m{ch}")
    return "".join(out) + "\x1b[0m"


def _centre(text: str, width: int) -> str:
    vis = _display_width(_strip_ansi(text))
    pad = max(0, (width - vis) // 2)
    return " " * pad + text


def _pad_line(text: str, width: int) -> str:
    """Return text padded with spaces to fill `width` visible chars (clears old content)."""
    vis = _display_width(_strip_ansi(text))
    return text + " " * max(0, width - vis)


def _render(cache: _Cache, width: int, t: float) -> str:
    rows: List[str] = []

    def row(s: str = "") -> None:
        rows.append(_pad_line(s, width))

    # ── header ──────────────────────────────────────────────────
    row()
    if cache.np and cache.np.title:
        np = cache.np
        row(_centre(f"\x1b[1;38;2;255;230;100m{np.title}\x1b[0m", width))
        row(_centre(f"\x1b[38;2;160;155;190m{np.artist or '—'}\x1b[0m", width))
    else:
        row(_centre("\x1b[38;2;120;130;130m(no track)\x1b[0m", width))
        row()
    row()

    # ── lyrics ──────────────────────────────────────────────────
    context = 3
    total_lyric_rows = context * 2 + 1

    if cache.cues and cache.is_lrc:
        pos = _live_pos(cache)
        idx = _index_for_position(cache.cues, pos)

        if idx != cache.last_idx:
            cache.last_idx = idx
            cache.last_change_t = t

        flash = max(0.0, 1.0 - (t - cache.last_change_t) / 0.35)

        for offset in range(-context, context + 1):
            i = idx + offset
            if i < 0 or i >= len(cache.cues):
                row()
                continue
            text = cache.cues[i][1]
            if offset == 0:
                row(_centre(f"\x1b[38;2;100;210;120m▶\x1b[0m {_wave_line(text, t, flash)}", width))
            else:
                dist = abs(offset)
                r, g, b = _FADE[min(dist - 1, len(_FADE) - 1)]
                row(_centre(f"  \x1b[38;2;{r};{g};{b}m{text}\x1b[0m", width))

    elif cache.plain_lines:
        np = cache.np
        pos = _live_pos(cache)
        dur = np.duration if np else 0.0
        if dur > 0:
            ratio = min(1.0, pos / dur)
            idx = int(ratio * (len(cache.plain_lines) - 1))
        else:
            idx = 0
        for offset in range(-context, context + 1):
            i = idx + offset
            if i < 0 or i >= len(cache.plain_lines):
                row()
                continue
            text = cache.plain_lines[i]
            if offset == 0:
                row(_centre(f"\x1b[38;2;100;210;120m▶\x1b[0m {_wave_line(text, t, 0.0)}", width))
            else:
                dist = abs(offset)
                r, g, b = _FADE[min(dist - 1, len(_FADE) - 1)]
                row(_centre(f"  \x1b[38;2;{r};{g};{b}m{text}\x1b[0m", width))

    elif cache.lyrics is None and cache.np and cache.np.title:
        # Still loading
        dots = "." * (int(t * 2) % 4)
        row(_centre(f"\x1b[38;2;120;130;130m  fetching lyrics{dots}\x1b[0m", width))
        for _ in range(total_lyric_rows - 1):
            row()
    else:
        row(_centre("\x1b[38;2;80;80;100m  (no lyrics available)\x1b[0m", width))
        for _ in range(total_lyric_rows - 1):
            row()

    # ── bottom bar ──────────────────────────────────────────────
    row()
    if cache.np and cache.np.title:
        pos = _live_pos(cache)
        dur = cache.np.duration or 0.0
        inner = width - 4
        row("  " + render_spectrum_color(pos, width=inner, t=t))
        row("  " + render_progress(pos, dur, width=inner))
    else:
        row()
        row()
    row()

    return "\n".join(rows)


_HIDE = "\x1b[?25l"
_SHOW = "\x1b[?25h"
_ALT  = "\x1b[?1049h"
_NORM = "\x1b[?1049l"
_HOME = "\x1b[H"


def _setup_raw_tty():
    try:
        import termios, tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setraw(fd)
        return fd, old
    except Exception:
        return None


def _restore_tty(raw_state) -> None:
    if raw_state is None:
        return
    try:
        import termios
        fd, old = raw_state
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        pass


def _read_key(raw_state) -> str:
    if raw_state is None:
        return ""
    try:
        import select
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1)
    except Exception:
        pass
    return ""


def run(width: int = 0) -> int:
    import shutil
    _width = [width if width > 0 else shutil.get_terminal_size((80, 24)).columns]

    cache = _Cache()
    st = state.load()
    src = get_source(st.source)
    _poll(src, cache)

    raw_state = _setup_raw_tty()

    sys.stdout.write(_ALT + _HIDE)
    sys.stdout.flush()

    def _restore(*_):
        _restore_tty(raw_state)
        sys.stdout.write(_SHOW + _NORM)
        sys.stdout.flush()
        sys.exit(0)

    def _resize(*_):
        _width[0] = shutil.get_terminal_size((80, 24)).columns

    signal.signal(signal.SIGINT, _restore)
    signal.signal(signal.SIGTERM, _restore)
    signal.signal(signal.SIGWINCH, _resize)

    interval = 1.0 / FRAME_HZ
    try:
        while True:
            key = _read_key(raw_state)
            if key in ("q", "Q", "\x03"):
                break
            elif key == " ":
                src.toggle()
                _poll(src, cache)
            elif key in ("n", "N"):
                src.next()
                time.sleep(0.4)
                _poll(src, cache)
            elif key in ("p", "P"):
                src.prev()
                time.sleep(0.4)
                _poll(src, cache)
            elif key in ("l", "L"):
                try:
                    src.like_current()
                except Exception:
                    pass

            t = time.time()
            if t - cache.last_poll >= POLL_EVERY:
                _poll(src, cache)
            term_h = shutil.get_terminal_size((80, 24)).lines
            frame = _render(cache, _width[0], t)
            lines = frame.split("\n")
            clipped = "\n".join(lines[:term_h - 1])
            sys.stdout.write(_HOME + clipped + "\x1b[J")
            sys.stdout.flush()
            time.sleep(interval)
    finally:
        _restore_tty(raw_state)
        sys.stdout.write(_SHOW + _NORM)
        sys.stdout.flush()
    return 0
