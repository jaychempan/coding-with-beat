"""Compact real-time watch mode — local render from JSON snapshot.

Layout (adaptive to terminal size):
  ┌─── left 60% ───┬─── right 40% ───┐
  │  player        │                 │
  │  progress      │  queue list     │
  │  spectrum      │  (full height)  │
  ├────────────────┤                 │
  │  lyrics        │                 │
  │  (more lines)  │                 │
  │  DJ buddy      │                 │
  │  hint bar      │                 │
  └────────────────┴─────────────────┘
"""

from __future__ import annotations

import json
import shutil
import signal
import sys
import time

from . import dj
from ._tui import (
    CLEAR,
    enter_alt_screen,
    exit_alt_screen,
    read_key,
    restore_tty,
    setup_raw_tty,
)
from .config import DATA_DIR
from .mcp_client import MCPClientError, call_tool
from .ui.frame import _strip_ansi
from .ui.lyrics import _display_width, render_lyrics_window
from .ui.progress import render_progress, render_spectrum_color

FETCH_EVERY = 2.0
RENDER_EVERY = 0.05

_ACCENT = (155, 188, 15)
_DIM = "\x1b[38;2;100;110;100m"
_BOLD = "\x1b[1;38;2;220;230;220m"
_GREEN = "\x1b[38;2;155;188;15m"
_CUR = "\x1b[1;38;2;255;230;100m"
_RESET = "\x1b[0m"


def _fetch(known_key: str = "") -> dict:
    raw = call_tool("now_playing_snapshot", {"known_lyrics_key": known_key})
    return json.loads(raw)


def _interp_pos(snap: dict) -> float:
    pos = float(snap.get("position", 0.0))
    if snap.get("playing"):
        pos += time.time() - float(snap.get("sampled_at", time.time()))
    dur = float(snap.get("duration", 0.0))
    return max(0.0, min(pos, dur) if dur > 0 else pos)


def _control(tool: str) -> None:
    try:
        call_tool(tool)
    except MCPClientError:
        pass


def _sep(width: int) -> str:
    return _DIM + "─" * max(1, width) + _RESET


def _vis_len(s: str) -> int:
    return _display_width(_strip_ansi(s))


def _pad(s: str, width: int) -> str:
    """Pad an ANSI string to exactly `width` visible columns."""
    return s + " " * max(0, width - _vis_len(s))


def _trunc(s: str, width: int) -> str:
    """Truncate a plain string to `width` visible chars."""
    if _display_width(s) <= width:
        return s
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _display_width(s[:mid]) <= width - 1:
            lo = mid
        else:
            hi = mid - 1
    return s[:lo] + "…"


def _load_queue() -> tuple[list[dict], int]:
    try:
        tracks = json.loads((DATA_DIR / "last_results.json").read_text(encoding="utf-8"))
    except Exception:
        tracks = []
    try:
        cur_idx = int(
            json.loads((DATA_DIR / "queue_index.json").read_text(encoding="utf-8")).get("index", -1)
        )
    except Exception:
        cur_idx = -1
    return tracks, cur_idx


def _render_player_top(snap: dict, width: int, height: int, t: float) -> list[str]:
    """Top-left panel: title, progress, spectrum (compact, no sprite)."""
    title = snap.get("title") or "—"
    artist = snap.get("artist") or ""
    playing = snap.get("playing", False)
    dur = float(snap.get("duration", 0.0))
    pos = _interp_pos(snap)

    icon = f"{_GREEN}▶{_RESET}" if playing else f"{_DIM}❚❚{_RESET}"
    rows: list[str] = [
        "",
        f" {icon}  {_BOLD}{_trunc(title, width - 6)}{_RESET}",
    ]
    if artist:
        rows.append(f"    {_DIM}{_trunc(artist, width - 5)}{_RESET}")
    rows += [
        _sep(width),
        " " + render_progress(pos, dur, max(1, width - 17), _ACCENT),
        " " + render_spectrum_color(pos, max(1, width - 2), t=t),
        _sep(width),
    ]

    while len(rows) < height:
        rows.append("")
    return [_pad(r, width) for r in rows[:height]]


def _render_lyrics_bottom(
    lyrics_text: str, pos: float, dur: float, width: int, height: int, playing: bool
) -> list[str]:
    """Bottom-left panel: lyrics (top) ─── 4-line sprite + hint (bottom-left)."""
    # Small 4-line animated sprite from DANCE_FRAMES — fits neatly at the corner.
    frame_idx = int(time.time() * 2)
    mood = "groove" if playing else "neutral"
    sprite_lines = dj.sprite_frame(mood, frame_idx).split("\n")
    sprite_h = len(sprite_lines)
    hint = f" {_DIM}space pause  n next  p prev  l like  q quit{_RESET}"

    # Layout: [lyrics × lyrics_h] [sep] [sprite × sprite_h] [hint]
    lyrics_h = max(1, height - sprite_h - 2)  # 2 = sep + hint

    if lyrics_text:
        # Fill the whole lyrics section — no half-empty window.
        raw = render_lyrics_window(lyrics_text, pos, dur, window=lyrics_h, width=width - 1)
        content = [" " + ln for ln in raw.split("\n")]
    else:
        content = [f" {_DIM}(no lyrics){_RESET}"]

    while len(content) < lyrics_h:
        content.append("")
    content = content[:lyrics_h]

    rows = content + [_sep(width)] + sprite_lines + [hint]
    while len(rows) < height:
        rows.append("")
    return [_pad(r, width) for r in rows[:height]]


def _render_queue_lines(tracks: list[dict], cur_idx: int, width: int, height: int) -> list[str]:
    """Right panel: scrollable queue list, no line wrapping."""
    header = _pad(f" {_DIM}Queue ({len(tracks)}){_RESET}", width)
    rows: list[str] = ["", header, _sep(width)]

    if not tracks:
        rows.append(_pad(f" {_DIM}run cwb list to load queue{_RESET}", width))
    else:
        visible = max(1, height - len(rows))
        # Scroll so current track is centered
        start = max(0, cur_idx - visible // 2) if cur_idx >= 0 else 0
        end = min(len(tracks), start + visible)
        start = max(0, end - visible)

        # Right-align numbers so "1." and "22." end at the same column.
        # Prefix is always 3 visible chars (" > " or "   ") + num_w + 1 space.
        # Using ">" (ASCII) instead of "▶" avoids East-Asian ambiguous-width rendering.
        num_w = len(str(len(tracks))) + 1  # chars for "N." at max track count
        title_w = max(1, width - num_w - 4)  # 3 (indicator) + 1 (space after num)

        for i in range(start, end):
            num = f"{i + 1}."
            num_str = f"{num:>{num_w}}"
            title = _trunc(tracks[i].get("title", "?"), title_w)
            if i == cur_idx:
                line = _pad(f" {_CUR}> {num_str} {title}{_RESET}", width)
            else:
                line = _pad(f"   {_DIM}{num_str}{_RESET} {title}", width)
            rows.append(line)

    while len(rows) < height:
        rows.append(" " * width)
    return [_pad(r, width) for r in rows[:height]]


def _compose3(
    top_left: list[str],
    bot_left: list[str],
    right: list[str],
    left_w: int,
    total_h: int,
) -> str:
    """Merge three panels into a frame.

    Rows 0..top_h-1  : top_left │ right
    Row  top_h       : ──────────┤ right   (horizontal divider)
    Rows top_h+1..   : bot_left  │ right
    """
    vsep = f"{_DIM}│{_RESET}"
    top_h = len(top_left)
    hjunction = _DIM + "─" * left_w + "┤" + _RESET

    out = []
    for i in range(total_h):
        r = right[i] if i < len(right) else ""
        if i < top_h:
            l = top_left[i]
            out.append(f"{l}{vsep}{r}")
        elif i == top_h:
            out.append(f"{hjunction}{r}")
        else:
            bi = i - top_h - 1
            l = bot_left[bi] if bi < len(bot_left) else " " * left_w
            out.append(f"{l}{vsep}{r}")
    return "\n".join(out)


def run(width: int = 0) -> int:
    sz = [shutil.get_terminal_size((80, 24))]
    _width = [width if width > 0 else sz[0].columns]
    raw = setup_raw_tty()

    enter_alt_screen()

    def _quit(*_):
        restore_tty(raw)
        exit_alt_screen()
        sys.exit(0)

    def _resize(*_):
        sz[0] = shutil.get_terminal_size((80, 24))
        _width[0] = sz[0].columns
        sys.stdout.write(CLEAR)
        sys.stdout.flush()

    signal.signal(signal.SIGINT, _quit)
    signal.signal(signal.SIGTERM, _quit)
    signal.signal(signal.SIGWINCH, _resize)

    snap: dict = {}
    lyrics_text = ""
    lyrics_key = ""
    last_fetch = 0.0
    last_render = 0.0
    queue: list[dict] = []
    cur_idx = -1

    try:
        while True:
            key = read_key(raw)
            if key in ("q", "Q", "\x03"):
                break
            if key == " ":
                _control("toggle")
                last_fetch = 0.0
            elif key in ("n", "N"):
                _control("next_track")
                last_fetch = 0.0
            elif key in ("p", "P"):
                _control("prev_track")
                last_fetch = 0.0
            elif key in ("l", "L"):
                _control("like_current")

            now = time.time()

            if now - last_fetch >= FETCH_EVERY:
                try:
                    new = _fetch(lyrics_key)
                    if new.get("lyrics_text"):
                        lyrics_text = new["lyrics_text"]
                        lyrics_key = new.get("lyrics_key", "")
                    elif new.get("lyrics_key") and new["lyrics_key"] != lyrics_key:
                        lyrics_text = ""
                        lyrics_key = new["lyrics_key"]
                    snap = new
                    last_fetch = now
                except MCPClientError:
                    pass
                queue, cur_idx = _load_queue()

            if snap and now - last_render >= RENDER_EVERY:
                total_w = _width[0]
                h = sz[0].lines
                # Usable rows: h-1 (last terminal line reserved to prevent scroll)
                usable_h = h - 1
                left_w = max(20, int(total_w * 0.6))
                right_w = max(10, total_w - left_w - 1)  # 1 col for │

                # Player section: compact 8 rows (no sprite).
                # Bottom section: lyrics + sep + 4-line sprite + hint.
                _SPRITE_H = 4  # DANCE_FRAMES sprite is always 4 lines
                _min_top = 8
                _min_bot = _SPRITE_H + 2 + 2  # sprite + sep + hint + 2 lyrics
                if usable_h >= _min_top + 1 + _min_bot:
                    top_h = _min_top
                    bot_h = usable_h - top_h - 1
                else:
                    top_h = max(5, usable_h // 2)
                    bot_h = max(3, usable_h - top_h - 1)

                pos = _interp_pos(snap)
                dur = float(snap.get("duration", 0.0))
                playing = snap.get("playing", False)

                player_lines = _render_player_top(snap, left_w, top_h, now)
                lyrics_lines = _render_lyrics_bottom(lyrics_text, pos, dur, left_w, bot_h, playing)
                queue_lines = _render_queue_lines(queue, cur_idx, right_w, usable_h)
                frame = _compose3(player_lines, lyrics_lines, queue_lines, left_w, usable_h)

                lines = frame.split("\n")
                out = []
                for i, line in enumerate(lines[:usable_h]):
                    out.append(f"\x1b[{i + 1};1H{line}\x1b[K")
                out.append(f"\x1b[{usable_h + 1};1H\x1b[J")
                sys.stdout.write("".join(out))
                sys.stdout.flush()
                last_render = now

            time.sleep(0.02)
    finally:
        restore_tty(raw)
        exit_alt_screen()
    return 0
