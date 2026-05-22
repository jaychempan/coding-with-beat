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
import math
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
JUMP_ROWS = 3  # max rows the sprite can lift above ground
_SPRITE_W = 10  # visible width of pixel-person frame

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
        cur_idx = int(json.loads((DATA_DIR / "queue_index.json").read_text(encoding="utf-8")).get("index", -1))
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
    ]

    while len(rows) < height:
        rows.append("")
    return [_pad(r, width) for r in rows[:height]]


def _render_lyrics_bottom(
    lyrics_text: str, pos: float, dur: float, width: int, height: int, playing: bool, t: float = 0.0
) -> list[str]:
    """Bottom-left panel: lyrics (top) + animated pixel person walking/jumping below."""
    mood = "groove" if playing else "neutral"
    sprite_h = 7  # pixel-person frames are always 7 lines
    stage_h = sprite_h + JUMP_ROWS  # rows reserved for sprite + jump headroom

    show_sprite = height > stage_h + 1  # need at least 1 lyric row + separator
    if not show_sprite:
        stage_h = 0

    lyrics_h = max(1, height - stage_h - (1 if show_sprite else 0))

    if lyrics_text:
        raw = render_lyrics_window(lyrics_text, pos, dur, window=lyrics_h, width=width - 1)
        content = [" " + ln for ln in raw.split("\n")]
    else:
        content = [f" {_DIM}(no lyrics){_RESET}"]

    while len(content) < lyrics_h:
        content.append("")
    content = content[:lyrics_h]

    if show_sprite:
        # ── jump: pseudo-random per 4-second window via golden-ratio hash ──
        bucket = int(t / 4.0)
        will_jump = (math.sin(bucket * 1.6180339) + 1.0) / 2.0 > 0.4
        if will_jump:
            t_local = (t % 4.0) / 4.0
            y_lift = max(0.0, math.sin(t_local * math.pi))
            y = int(y_lift * JUMP_ROWS)
        else:
            y = 0

        # ── horizontal walk: two incommensurable sine waves ──
        max_x = max(0, width - _SPRITE_W)
        x_frac = 0.5 + 0.4 * math.sin(t * 0.31) + 0.1 * math.sin(t * 0.73)
        x_frac = max(0.0, min(1.0, x_frac))
        x_offset = int(x_frac * max_x)

        # ── frame: arms-up when airborne, shimmy direction otherwise ──
        if will_jump and y > 0:
            frame_idx = 1
        else:
            frame_idx = 2 if math.sin(t * 0.31) < 0 else 0

        sprite_lines = dj.pixel_person_frame(mood, frame_idx).split("\n")

        # Place sprite in vertical stage (y=0 → on ground; y=JUMP_ROWS → airborne)
        top_blank = JUMP_ROWS - y
        bottom_blank = y
        stage_rows = [""] * top_blank + sprite_lines + [""] * bottom_blank

        # Apply horizontal offset
        positioned = [_pad(" " * x_offset + line, width) for line in stage_rows]
        rows = content + [_sep(width)] + positioned
    else:
        rows = content

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
            track = tracks[i]
            title_str = _trunc(track.get("title", "?"), title_w)
            artist = track.get("artist", "")
            spare = title_w - _display_width(title_str) - 2
            art_sfx = f"  {_DIM}{_trunc(artist, spare)}{_RESET}" if artist and spare > 0 else ""
            if i == cur_idx:
                line = _pad(f" {_CUR}> {num_str} {title_str}{_RESET}{art_sfx}", width)
            else:
                line = _pad(f"   {_DIM}{num_str}{_RESET} {title_str}{art_sfx}", width)
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
            lc = top_left[i]
            out.append(f"{lc}{vsep}{r}")
        elif i == top_h:
            out.append(f"{hjunction}{r}")
        else:
            bi = i - top_h - 1
            lc = bot_left[bi] if bi < len(bot_left) else " " * left_w
            out.append(f"{lc}{vsep}{r}")
    return "\n".join(out)


def run(width: int = 0) -> int:
    sz = [shutil.get_terminal_size((80, 24))]
    _width = [width if width > 0 else sz[0].columns]
    raw = setup_raw_tty()

    enter_alt_screen()
    # Re-read after alt screen is established; the first read may be stale.
    sz[0] = shutil.get_terminal_size((80, 24))
    _width[0] = sz[0].columns

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
                # Keep queue highlight in sync even when Apple Music plays
                # a track not triggered via cwb (queue_index.json would be stale).
                if snap.get("title") and queue and cur_idx < len(queue):
                    playing_title = snap["title"]
                    if queue[cur_idx].get("title", "") != playing_title:
                        for j, t in enumerate(queue):
                            if t.get("title", "") == playing_title:
                                cur_idx = j
                                break

            if snap and now - last_render >= RENDER_EVERY:
                total_w = _width[0]
                h = sz[0].lines
                # usable_h: everything except the very last terminal line.
                # sep_h:     full-width ── separator closing the panels.
                # panels_h:  two rows less — panels end before the separator.
                usable_h = h - 1
                sep_h = usable_h - 1
                panels_h = sep_h - 1
                left_w = max(20, int(total_w * 0.65))
                right_w = max(10, total_w - left_w - 1)  # 1 col for │

                # Player section height = exactly its content rows — no blank
                # padding before the ────────┤ junction.
                _player_rows = 5 + (1 if snap.get("artist") else 0)
                top_h = _player_rows
                bot_h = max(3, panels_h - top_h - 1)

                pos = _interp_pos(snap)
                dur = float(snap.get("duration", 0.0))
                playing = snap.get("playing", False)

                player_lines = _render_player_top(snap, left_w, top_h, now)
                lyrics_lines = _render_lyrics_bottom(lyrics_text, pos, dur, left_w, bot_h, playing, now)
                queue_lines = _render_queue_lines(queue, cur_idx, right_w, panels_h)
                frame = _compose3(player_lines, lyrics_lines, queue_lines, left_w, panels_h)

                hint_text = "space pause  n next  p prev  l like  q quit"
                hint_styled = f"{_DIM}{hint_text}{_RESET}"
                hint_pad = max(0, (total_w - len(hint_text)) // 2)
                hint_line = " " * hint_pad + hint_styled

                lines = frame.split("\n")
                out = []
                for i, line in enumerate(lines[:panels_h]):
                    out.append(f"\x1b[{i + 1};1H{line}\x1b[K")
                out.append(f"\x1b[{sep_h};1H{_DIM}{'─' * total_w}{_RESET}\x1b[K")
                out.append(f"\x1b[{usable_h};1H{_pad(hint_line, total_w)}\x1b[K")
                out.append(f"\x1b[{usable_h + 1};1H\x1b[J")
                sys.stdout.write("".join(out))
                sys.stdout.flush()
                last_render = now

            time.sleep(0.02)
    finally:
        restore_tty(raw)
        exit_alt_screen()
    return 0
