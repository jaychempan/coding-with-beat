"""Compact real-time watch mode — local render from JSON snapshot."""

from __future__ import annotations

import json
import shutil
import signal
import sys
import time

from ._tui import (
    CLEAR,
    enter_alt_screen,
    exit_alt_screen,
    read_key,
    restore_tty,
    setup_raw_tty,
)
from . import dj
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
    """Pad an ANSI-escaped string to exactly `width` visible columns."""
    return s + " " * max(0, width - _vis_len(s))


def _trunc(s: str, width: int) -> str:
    """Truncate a plain string to `width` visible chars, appending '…' if cut."""
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


def _render_player_lines(snap: dict, lyrics_text: str, width: int, height: int, t: float) -> list[str]:
    title = snap.get("title") or "—"
    artist = snap.get("artist") or ""
    playing = snap.get("playing", False)
    dur = float(snap.get("duration", 0.0))
    pos = _interp_pos(snap)

    icon = f"{_GREEN}▶{_RESET}" if playing else f"{_DIM}❚❚{_RESET}"
    artist_part = f"  {_DIM}·  {artist}{_RESET}" if artist else ""
    title_line = f" {icon}  {_BOLD}{title}{_RESET}{artist_part}"

    bar_w = max(1, width - 16)
    spec_w = max(1, width - 2)

    rows = [
        "",
        title_line,
        _sep(width),
        " " + render_progress(pos, dur, bar_w, _ACCENT),
        " " + render_spectrum_color(pos, spec_w, t=t),
    ]

    if lyrics_text:
        rows.append(_sep(width))
        lrc = render_lyrics_window(lyrics_text, pos, dur, window=3, width=width)
        for line in lrc.split("\n"):
            rows.append(" " + line)

    rows.append(_sep(width))
    mood = "groove" if playing else "neutral"
    for line in dj.dancing_sprite(mood).split("\n"):
        rows.append(line)
    rows.append(_sep(width))
    rows.append(f" {_DIM}space pause  n next  p prev  l like  q quit{_RESET}")
    rows.append("")

    return [_pad(r, width) for r in rows]


def _render_queue_lines(tracks: list[dict], cur_idx: int, width: int, height: int) -> list[str]:
    header = _pad(f" {_DIM}Queue ({len(tracks)}){_RESET}", width)
    rows: list[str] = ["", header, _sep(width)]

    if not tracks:
        rows.append(_pad(f" {_DIM}(run cwb list to load queue){_RESET}", width))
    else:
        visible = max(1, height - len(rows) - 1)
        start = max(0, cur_idx - visible // 2) if cur_idx >= 0 else 0
        end = min(len(tracks), start + visible)
        start = max(0, end - visible)

        for i in range(start, end):
            num = f"{i + 1}."
            title = _trunc(tracks[i].get("title", "?"), width - 6)
            if i == cur_idx:
                line = _pad(f" {_CUR}▶ {num:<3}{title}{_RESET}", width)
            else:
                line = _pad(f" {_DIM}{num:<3}{_RESET}{title}", width)
            rows.append(line)

    while len(rows) < height:
        rows.append(" " * width)
    return rows[:height]


def _compose(left: list[str], right: list[str], height: int) -> str:
    vsep = f"{_DIM}│{_RESET}"
    out = []
    for i in range(min(height, max(len(left), len(right)))):
        l = left[i] if i < len(left) else ""
        r = right[i] if i < len(right) else ""
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
                height = sz[0].lines
                left_w = max(20, int(total_w * 0.6))
                right_w = max(10, total_w - left_w - 1)

                player_lines = _render_player_lines(snap, lyrics_text, left_w, height, now)
                queue_lines = _render_queue_lines(queue, cur_idx, right_w, height)
                frame = _compose(player_lines, queue_lines, height)

                lines = frame.split("\n")
                out = []
                for i, line in enumerate(lines[: height - 1]):
                    out.append(f"\x1b[{i + 1};1H{line}\x1b[K")
                last = min(len(lines), height - 1) + 1
                out.append(f"\x1b[{last};1H\x1b[J")
                sys.stdout.write("".join(out))
                sys.stdout.flush()
                last_render = now

            time.sleep(0.02)
    finally:
        restore_tty(raw)
        exit_alt_screen()
    return 0
